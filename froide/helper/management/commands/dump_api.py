import json
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import translation

from rest_framework.test import APIClient


class Command(BaseCommand):
    help = "Dump all objects from API URL as JSONL"

    def add_arguments(self, parser):
        parser.add_argument("url", type=str)

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)

        url = options["url"]

        server_name = settings.SITE_URL.rsplit("/", 1)[1]

        client = APIClient()
        total = None
        while True:
            parsed = urlparse(url)
            response = client.get(
                parsed.path,
                parse_qs(parsed.query),
                format="json",
                SERVER_NAME=server_name,
                secure=True,
            )
            for obj in response.data["objects"]:
                self.stdout.write(json.dumps(obj), ending="\n")
            offset = response.data["meta"]["offset"]
            if not total:
                total = response.data["meta"]["total_count"]
            if total:
                self.stderr.write("\r{:.1%}".format(offset / total), ending="")
            url = response.data["meta"]["next"]
            if not url:
                break
