import csv
import json
from io import BytesIO, StringIO

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.contrib.sites.models import Site
from django.utils import timezone
from django.utils.translation import gettext as _

import requests

from froide.georegion.models import GeoRegion
from froide.helper.text_utils import slugify
from froide.publicbody.models import Category, Classification, Jurisdiction, PublicBody

User = get_user_model()


class CSVImporter(object):
    def __init__(self, user=None):
        if user is None:
            self.user = User.objects.order_by("id")[0]
        else:
            self.user = user
        self.site = Site.objects.get_current()
        self.topic_cache = {}
        self.classification_cache = {}
        self.default_topic = None
        self.jur_cache = {}
        self.category_cache = {}

    def import_from_url(self, url):
        response = requests.get(url)
        # Force requests to evaluate as UTF-8
        response.encoding = "utf-8"
        csv_file = BytesIO(response.content)
        self.import_from_file(csv_file)

    def import_from_file(self, csv_file):
        """
        csv_file should be encoded in utf-8
        """
        csv_file = StringIO(csv_file.read().decode("utf-8"))
        reader = csv.DictReader(csv_file)
        for row in reader:
            self.import_row(row)

    def import_row(self, row):
        # generate slugs
        if "name" in row:
            row["name"] = row["name"].strip()

        if "email" in row:
            row["email"] = row["email"].lower()

        if "url" in row:
            if row["url"] and not row["url"].startswith(("http://", "https://")):
                row["url"] = "http://" + row["url"]

        if "slug" not in row and "name" in row:
            row["slug"] = slugify(row["name"])

        if "classification" in row:
            row["classification"] = self.get_classification(
                row.pop("classification", None)
            )

        categories = row.pop("categories", [])
        if categories:
            categories_list = categories.split(",")
            categories = list(self.get_categories(categories_list))

        # resolve foreign keys
        if "jurisdiction__slug" in row:
            row["jurisdiction"] = self.get_jurisdiction(row.pop("jurisdiction__slug"))

        regions = None
        if "georegion_id" in row:
            regions = [self.get_georegion(id=row.pop("georegion_id"))]
        elif "georegion_identifier" in row:
            regions = [self.get_georegion(identifier=row.pop("georegion_identifier"))]
        elif "regions" in row:
            regions = row.pop("regions")
            if regions:
                regions = [self.get_georegion(id=r) for r in regions.split(",")]

        parent = row.pop("parent__name", None)
        if parent:
            row["parent"] = PublicBody._default_manager.get(slug=slugify(parent))

        parent = row.pop("parent__id", None)
        if parent:
            row["parent"] = PublicBody._default_manager.get(pk=parent)

        extra_data = row.pop("extra_data", None)
        if extra_data:
            row["extra_data"] = json.loads(extra_data)

        alternative_emails = row.pop("alternative_emails", None)
        if alternative_emails:
            row["alternative_emails"] = json.loads(alternative_emails)

        # get optional values
        for n in (
            "fax",
            "source_reference",
            "description",
            "other_names",
            "request_note",
            "website_dump",
            "wikidata_item",
        ):
            if n in row:
                row[n] = row[n].strip()

        if "lat" in row and "lng" in row:
            lat = row.pop("lat")
            lng = row.pop("lng")
            if lat and lng:
                row["geo"] = Point(float(lng), float(lat))

        try:
            if "id" in row and row["id"]:
                pb = PublicBody._default_manager.get(id=row["id"])
            elif row.get("source_reference"):
                pb = PublicBody._default_manager.get(
                    source_reference=row["source_reference"]
                )
            else:
                pb = PublicBody._default_manager.get(slug=row["slug"])
            # If it exists, update it
            row.pop("id", None)  # Do not update id though
            row.pop("slug", None)  # Do not update slug either
            row["_updated_by"] = self.user
            row["updated_at"] = timezone.now()
            PublicBody._default_manager.filter(id=pb.id).update(**row)
            if row.get("jurisdiction"):
                pb.laws.clear()
                pb.laws.add(*row["jurisdiction"].laws)
            if regions:
                pb.regions.set(regions)
            if categories:
                pb.categories.set(*categories)
            return pb
        except PublicBody.DoesNotExist:
            pass
        row.pop("id", None)  # Remove id if present
        pb = PublicBody(**row)
        pb._created_by = self.user
        pb._updated_by = self.user
        pb.created_at = timezone.now()
        pb.updated_at = timezone.now()
        pb.confirmed = True
        pb.site = self.site
        pb.save()
        if row.get("jurisdiction"):
            pb.laws.add(*row["jurisdiction"].laws)
        if regions:
            pb.regions.set(regions)
        if categories:
            pb.categories.set(*categories)
        return pb

    def get_jurisdiction(self, slug):
        if slug not in self.jur_cache:
            try:
                jur = Jurisdiction.objects.get(slug=slug)
            except Jurisdiction.DoesNotExist:
                raise ValueError(_('Jurisdiction slug "%s" does not exist.') % slug)
            jur.laws = jur.get_all_laws()
            self.jur_cache[slug] = jur
        return self.jur_cache[slug]

    def get_categories(self, cats):
        for cat in cats:
            if cat in self.category_cache:
                yield self.category_cache[cat]
            else:
                try:
                    try:
                        id = int(cat)
                        category = Category.objects.get(id=id)
                    except ValueError:
                        cat_string = str(cat).replace('"', "")
                        category = Category.objects.get(name=cat_string)
                except Category.DoesNotExist:
                    raise ValueError(_('Category name "%s" does not exist.') % cat)
                self.category_cache[cat] = category
                yield category

    def get_georegion(self, id=None, identifier=None, name=None):
        try:
            if id is not None:
                return GeoRegion.objects.get(id=id)
            if identifier is not None:
                return GeoRegion.objects.get(region_identifier=identifier)
        except GeoRegion.DoesNotExist:
            raise ValueError(_("GeoRegion %s/%s does not exist.") % (id, identifier))
        return None

    def get_classification(self, name):
        if not name:
            return None
        if name not in self.classification_cache:
            try:
                self.classification_cache[name] = Classification.objects.get(name=name)
            except Classification.DoesNotExist:
                raise ValueError(_('Classification "%s" does not exist.') % name)
        return self.classification_cache[name]
