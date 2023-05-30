import itertools
import unittest
import urllib.parse
from datetime import datetime, timezone
from typing import Callable, Optional
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.test.utils import override_settings
from django.urls import resolve, reverse

import pytest
from bs4 import BeautifulSoup
from pytest_django.asserts import (
    assertContains,
    assertInHTML,
    assertNotContains,
    assertNumQueries,
    assertRedirects,
)

from froide.foirequest.filters import FOIREQUEST_LIST_FILTER_CHOICES
from froide.foirequest.models import FoiAttachment, FoiRequest
from froide.foirequest.tests import factories
from froide.helper.search.signal_processor import realtime_search
from froide.publicbody.models import Category, FoiLaw, Jurisdiction, PublicBody

User = get_user_model()
MEDIA_DOMAIN = "media.frag-den-staat.de"


def assertForbidden(response):
    assert response.status_code == 302
    assert reverse("account-login") in response["Location"]
    assert "?next=" in response["Location"]


@pytest.mark.django_db
def test_index(world, client):
    response = client.get("/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_request(world, client):
    response = client.get(reverse("foirequest-make_request"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_request_to(world, client):
    p = PublicBody.objects.all()[0]
    response = client.get(
        reverse("foirequest-make_request", kwargs={"publicbody_slug": p.slug})
    )
    assert response.status_code == 200
    p.email = ""
    p.save()
    response = client.get(
        reverse("foirequest-make_request", kwargs={"publicbody_slug": p.slug})
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_request_prefilled(world, client):
    p = PublicBody.objects.all()[0]
    response = client.get(
        reverse("foirequest-make_request", kwargs={"publicbody_slug": p.slug})
        + "?body=THEBODY&subject=THESUBJECT"
    )
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "THEBODY" in content
    assert "THESUBJECT" in content


@unittest.skip("No longer redirect to slug on pb ids")
@pytest.mark.django_db
def test_request_prefilled_redirect(world, client):
    p = PublicBody.objects.all()[0]
    query = "?body=THEBODY&subject=THESUBJECT"
    response = client.get(
        reverse("foirequest-make_request", kwargs={"publicbody_ids": str(p.pk)}) + query
    )
    assertRedirects(
        response,
        reverse("foirequest-make_request", kwargs={"publicbody_slug": p.slug}) + query,
        status_code=200,
    )


@pytest.mark.django_db
def test_list_requests(world, client):
    factories.rebuild_index()
    response = client.get(reverse("foirequest-list"))
    assert response.status_code == 200
    for slug, _label in FOIREQUEST_LIST_FILTER_CHOICES:
        request_list_url = reverse("foirequest-list", kwargs={"status": slug})
        response = client.get(request_list_url)
        assert response.status_code == 200

    for topic in Category.objects.filter(is_topic=True):
        response = client.get(
            reverse("foirequest-list", kwargs={"category": topic.slug})
        )
        assert response.status_code == 200

    bad_request_list_url = request_list_url.replace(str(slug), "bad")
    response = client.get(bad_request_list_url)
    assert response.status_code == 404

    response = client.get(reverse("foirequest-list") + "?page=99999")
    assert response.status_code == 404


@pytest.mark.django_db
def test_list_jurisdiction_requests(world, client):
    factories.rebuild_index()
    juris = Jurisdiction.objects.all()[0]
    response = client.get(
        reverse("foirequest-list", kwargs={"jurisdiction": juris.slug})
    )
    assert response.status_code == 200

    response = client.get(
        reverse("foirequest-list", kwargs={"jurisdiction": "bad-juris"})
    )
    assert response.status_code == 404

    for slug, _label in FOIREQUEST_LIST_FILTER_CHOICES:
        response = client.get(
            reverse(
                "foirequest-list",
                kwargs={"status": slug, "jurisdiction": juris.slug},
            )
        )
        assert response.status_code == 200

    for topic in Category.objects.filter(is_topic=True):
        response = client.get(
            reverse(
                "foirequest-list",
                kwargs={"category": topic.slug, "jurisdiction": juris.slug},
            )
        )
        assert response.status_code == 200


@pytest.mark.django_db
def test_tagged_requests(world, client):
    tag_slug = "awesome"
    req = FoiRequest.published.all()[0]
    req.tags.add(tag_slug)
    req.save()
    factories.rebuild_index()

    response = client.get(reverse("foirequest-list", kwargs={"tag": tag_slug}))
    assert response.status_code == 200
    assertContains(response, req.title)
    response = client.get(reverse("foirequest-list_feed", kwargs={"tag": tag_slug}))
    assert response.status_code == 200
    response = client.get(
        reverse("foirequest-list_feed_atom", kwargs={"tag": tag_slug})
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_publicbody_requests(world, client):
    factories.rebuild_index()
    req = FoiRequest.published.all()[0]
    pb = req.public_body
    response = client.get(reverse("foirequest-list", kwargs={"publicbody": pb.slug}))
    assert response.status_code == 200
    assertContains(response, req.title)
    response = client.get(
        reverse("foirequest-list_feed", kwargs={"publicbody": pb.slug})
    )
    assert response.status_code == 200
    response = client.get(
        reverse("foirequest-list_feed_atom", kwargs={"publicbody": pb.slug})
    )
    assert response.status_code == 200


@pytest.mark.django_db(transaction=True)
def test_list_no_identical(world, client):
    factories.FoiRequestFactory.create(site=world)
    factories.rebuild_index()
    reqs = FoiRequest.published.all()
    req1 = reqs[0]
    req2 = reqs[1]
    response = client.get(reverse("foirequest-list"))
    assert response.status_code == 200
    assertContains(response, req1.title)
    assertContains(response, req2.title)
    with realtime_search(world, client):
        req1.same_as = req2
        req1.save()
        req2.same_as_count = 1
        req2.save()

    response = client.get(reverse("foirequest-list"))
    assert response.status_code == 200
    assertNotContains(response, req1.title)
    assertContains(response, req2.title)


@pytest.mark.django_db
def test_show_request(world, client):
    req = FoiRequest.objects.all()[0]
    response = client.get(
        reverse("foirequest-show", kwargs={"slug": req.slug + "-garbage"})
    )
    assert response.status_code == 404
    response = client.get(reverse("foirequest-show", kwargs={"slug": req.slug}))
    assert response.status_code == 200
    req.visibility = 1
    req.save()
    response = client.get(reverse("foirequest-show", kwargs={"slug": req.slug}))
    assertForbidden(response)
    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.get(reverse("foirequest-show", kwargs={"slug": req.slug}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_short_link_request(world, client):
    req = FoiRequest.objects.all()[0]
    response = client.get(reverse("foirequest-shortlink", kwargs={"obj_id": 0}))
    assert response.status_code == 404
    response = client.get(reverse("foirequest-shortlink", kwargs={"obj_id": req.id}))
    assertRedirects(response, req.get_absolute_url())
    # Shortlinks may end in /
    response = client.get(
        reverse("foirequest-shortlink", kwargs={"obj_id": req.id}) + "/"
    )
    assertRedirects(response, req.get_absolute_url())
    req.visibility = FoiRequest.VISIBILITY.VISIBLE_TO_REQUESTER
    req.save()
    response = client.get(reverse("foirequest-shortlink", kwargs={"obj_id": req.id}))
    assertForbidden(response)


@pytest.mark.django_db
def test_auth_links(world, client):
    from froide.foirequest.auth import get_foirequest_auth_code

    req = FoiRequest.objects.all()[0]
    req.visibility = 1
    req.save()
    response = client.get(reverse("foirequest-show", kwargs={"slug": req.slug}))
    assertForbidden(response)
    response = client.get(
        reverse("foirequest-auth", kwargs={"obj_id": req.id, "code": "0a"})
    )
    assertForbidden(response)
    response = client.get(
        reverse(
            "foirequest-auth",
            kwargs={"obj_id": req.id, "code": get_foirequest_auth_code(req)},
        )
    )
    assert response.status_code == 302
    assert response["Location"].endswith(req.get_absolute_url())
    # Check logged in with wrong code
    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.get(
        reverse("foirequest-auth", kwargs={"obj_id": req.id, "code": "0a"})
    )
    assert response.status_code == 302
    assert response["Location"].endswith(req.get_absolute_url())


@pytest.mark.django_db
def test_feed(world, client):
    factories.rebuild_index()

    response = client.get(reverse("foirequest-feed_latest"))
    assertRedirects(response, reverse("foirequest-list_feed"), status_code=301)
    response = client.get(reverse("foirequest-feed_latest_atom"))
    assertRedirects(response, reverse("foirequest-list_feed_atom"), status_code=301)

    response = client.get(reverse("foirequest-list_feed"))
    assert response.status_code == 200
    response = client.get(reverse("foirequest-list_feed_atom"))
    assert response.status_code == 200

    juris = Jurisdiction.objects.all()[0]
    response = client.get(
        reverse("foirequest-list_feed", kwargs={"jurisdiction": juris.slug})
    )
    assert response.status_code == 200
    response = client.get(
        reverse("foirequest-list_feed_atom", kwargs={"jurisdiction": juris.slug})
    )
    assert response.status_code == 200

    topic = Category.objects.filter(is_topic=True)[0]
    response = client.get(
        reverse(
            "foirequest-list_feed",
            kwargs={"jurisdiction": juris.slug, "category": topic.slug},
        )
    )
    assert response.status_code == 200
    response = client.get(
        reverse(
            "foirequest-list_feed_atom",
            kwargs={"jurisdiction": juris.slug, "category": topic.slug},
        )
    )
    assert response.status_code == 200

    status = FOIREQUEST_LIST_FILTER_CHOICES[0][0]
    response = client.get(
        reverse(
            "foirequest-list_feed",
            kwargs={"jurisdiction": juris.slug, "status": status},
        )
    )
    assert response.status_code == 200
    response = client.get(
        reverse(
            "foirequest-list_feed_atom",
            kwargs={"jurisdiction": juris.slug, "status": status},
        )
    )
    assert response.status_code == 200

    req = FoiRequest.objects.all()[0]
    response = client.get(reverse("foirequest-feed_atom", kwargs={"slug": req.slug}))
    assert response.status_code == 200
    response = client.get(reverse("foirequest-feed", kwargs={"slug": req.slug}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_search(world, client):
    response = client.get(reverse("foirequest-search"))
    assert response.status_code == 302
    assert reverse("foirequest-list") in response["Location"]


@pytest.mark.django_db
@override_settings(
    SITE_URL="https://fragdenstaat.de",
    MEDIA_URL="https://" + MEDIA_DOMAIN + "/files/",
    ALLOWED_HOSTS=("fragdenstaat.de", MEDIA_DOMAIN),
)
@mock.patch(
    "froide.foirequest.auth.AttachmentCrossDomainMediaAuth.SITE_URL",
    "https://fragdenstaat.de",
)
def test_request_not_public(world, client):
    att = FoiAttachment.objects.filter(approved=True)[0]
    req = att.belongs_to.request
    req.visibility = 1
    req.save()
    response = client.get(
        att.get_absolute_domain_auth_url(), HTTP_HOST="fragdenstaat.de"
    )
    assertForbidden(response)
    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.get(
        att.get_absolute_domain_auth_url(), HTTP_HOST="fragdenstaat.de"
    )
    assert response.status_code == 302
    assert MEDIA_DOMAIN in response["Location"]
    response = client.get(response["Location"], HTTP_HOST=MEDIA_DOMAIN)
    assert response.status_code == 200
    assert "X-Accel-Redirect" in response
    assert response["X-Accel-Redirect"] == "%s%s" % (
        settings.INTERNAL_MEDIA_PREFIX,
        att.file.name,
    )


@pytest.mark.django_db
@override_settings(
    SITE_URL="https://fragdenstaat.de",
    MEDIA_URL="https://" + MEDIA_DOMAIN + "/files/",
    ALLOWED_HOSTS=("fragdenstaat.de", MEDIA_DOMAIN),
)
def test_request_media_tokens(world, client):
    att = FoiAttachment.objects.filter(approved=True)[0]
    req = att.belongs_to.request
    req.visibility = 1
    req.save()
    response = client.get(
        att.get_absolute_domain_auth_url(), HTTP_HOST="fragdenstaat.de"
    )
    assertForbidden(response)
    loggedin = client.login(email="info@fragdenstaat.de", password="froide")
    assert loggedin

    response = client.get(
        att.get_absolute_domain_auth_url().replace("?download", ""),
        follow=False,
        HTTP_HOST="fragdenstaat.de",
    )
    # permanent redirect to attachment page if no refresh
    assert response.status_code == 301
    redirect_url = response["Location"]
    assert redirect_url == att.get_absolute_url()

    # Simulate media refresh redirect
    response = client.get(
        att.get_absolute_domain_auth_url(),
        follow=False,
        HTTP_HOST="fragdenstaat.de",
    )
    # temporary redirect to media file
    assert response.status_code == 302
    redirect_url = response["Location"]

    _, _, domain, path = redirect_url.split("/", 3)
    response = client.get(
        "/" + path + "a",  # break signature
        follow=False,
        HTTP_HOST=domain,
    )
    assert response.status_code == 403
    response = client.get(
        "/" + path,
        follow=False,
        HTTP_HOST=domain,
    )
    assert response.status_code == 200
    assert response["X-Accel-Redirect"] == "%s%s" % (
        settings.INTERNAL_MEDIA_PREFIX,
        att.file.name,
    )
    assert response["Link"] == '<{}>; rel="canonical"'.format(
        att.get_absolute_domain_url()
    )


@pytest.mark.django_db
@override_settings(
    SITE_URL="https://fragdenstaat.de",
    MEDIA_URL="https://" + MEDIA_DOMAIN + "/files/",
    ALLOWED_HOSTS=("fragdenstaat.de", MEDIA_DOMAIN),
    FOI_MEDIA_TOKEN_EXPIRY=0,
)
@mock.patch(
    "froide.foirequest.auth.AttachmentCrossDomainMediaAuth.TOKEN_MAX_AGE_SECONDS", 0
)
@mock.patch(
    "froide.foirequest.auth.AttachmentCrossDomainMediaAuth.SITE_URL",
    "https://fragdenstaat.de",
)
def test_request_media_tokens_expired(world, client):
    att = FoiAttachment.objects.filter(approved=True)[0]
    req = att.belongs_to.request
    req.visibility = 1
    req.save()

    client.login(email="info@fragdenstaat.de", password="froide")

    response = client.get(
        att.get_absolute_domain_auth_url(),
        follow=False,
        HTTP_HOST="fragdenstaat.de",
    )
    assert response.status_code == 302
    redirect_url = response["Location"]
    _, _, domain, path = redirect_url.split("/", 3)

    response = client.get(
        "/" + path,
        follow=False,
        HTTP_HOST=domain,
    )
    assert response.status_code == 302
    # Redirect back for re-authenticating
    redirect_url = response["Location"]
    _, _, domain, path = redirect_url.split("/", 3)
    assert domain == "fragdenstaat.de"
    assert "/" + path in att.get_absolute_domain_auth_url()


@pytest.mark.django_db
def test_attachment_not_approved(world, client):
    att = FoiAttachment.objects.filter(approved=False)[0]
    response = client.get(att.get_absolute_url())
    assertForbidden(response)
    client.login(email="info@fragdenstaat.de", password="froide")
    response = client.get(att.get_absolute_url())
    assert response.status_code == 200


@pytest.mark.django_db
def test_request_public(world, client):
    att = FoiAttachment.objects.filter(approved=True)[0]
    response = client.get(att.get_absolute_url())
    assert response.status_code == 200
    response = client.get(att.get_absolute_url() + "a")
    assert response.status_code == 404


@pytest.mark.django_db
def test_attachment_empty(world, client):
    att = FoiAttachment.objects.filter(approved=True)[0]
    att.file = ""
    att.save()
    response = client.get(att.get_absolute_domain_auth_url())
    assert response.status_code == 404


@pytest.mark.django_db
def test_attachment_pending(world, client):
    att = FoiAttachment.objects.filter(approved=True)[0]
    att.pending = True
    att.save()
    response = client.get(att.get_absolute_domain_auth_url())
    assert response.status_code == 404


@pytest.mark.django_db
def test_queries_foirequest(world, client):
    """
    FoiRequest page should query for non-loggedin users
    - FoiRequest (+1)
    - FoiRequest Tags (+1)
    - FoiMessages of that request (+1)
    - FoiAttachments of that request (+1)
    - FoiEvents of that request (+1)
    - FoiRequestFollowerCount (+1)
    - Delivery Status (+1)
    - Guides (+1)
    - ContentType + Comments for each FoiMessage (+2)
    """
    req = factories.FoiRequestFactory.create(site=world)
    factories.FoiMessageFactory.create(request=req, is_response=False)
    mes2 = factories.FoiMessageFactory.create(request=req)
    factories.FoiAttachmentFactory.create(belongs_to=mes2)
    ContentType.objects.clear_cache()
    with assertNumQueries(10):
        client.get(req.get_absolute_url())


@pytest.mark.django_db
def test_queries_foirequest_loggedin(world, client):
    """
    FoiRequest page should query for non-staff loggedin users
    - Django session + Django user (+3)
    - FoiRequest (+1)
    - FoiRequest Tags (+1)
    - User and group permissions (+2)
    - FoiMessages of that request (+1)
    - FoiAttachments of that request (+1)
    - FoiEvents of that request (+1)
    - FoiRequestFollowerCount + if following (+2)
    - Delivery Status (+1)
    - Guides (+1)
    - Problem reports - even for non-requester (+1)
    - ContentType + Comments for each FoiMessage (+2)
    """
    TOTAL_EXPECTED_REQUESTS = 16
    req = factories.FoiRequestFactory.create(site=world)
    factories.FoiMessageFactory.create(request=req, is_response=False)
    mes2 = factories.FoiMessageFactory.create(request=req)
    factories.FoiAttachmentFactory.create(belongs_to=mes2)
    client.login(email="dummy@example.org", password="froide")
    ContentType.objects.clear_cache()
    with assertNumQueries(TOTAL_EXPECTED_REQUESTS):
        client.get(req.get_absolute_url())


@pytest.fixture
def req_with_unordered_messages(
    foi_request_factory, foi_message_factory, faker
) -> FoiRequest:
    req_text = faker.text(max_nb_chars=1000)
    req = foi_request_factory(description=req_text)
    foi_message_factory(
        request=req,
        is_response=True,
        timestamp=datetime(2022, 1, 1, tzinfo=timezone.utc),
        plaintext="Some random response text",
        plaintext_redacted="Some random response text",
    )
    foi_message_factory(
        request=req,
        is_response=False,
        timestamp=datetime(2022, 1, 5, tzinfo=timezone.utc),
        plaintext=f"To whom it may concern\n\n{req_text}\n\nGreetings",
        plaintext_redacted=f"To whom it may concern\n\n{req_text}\n\nGreetings",
    )
    return req


@pytest.fixture
def req_with_ordered_messages(
    foi_request_factory, foi_message_factory, faker
) -> FoiRequest:
    req_text = faker.text(max_nb_chars=1000)
    req = foi_request_factory(description=req_text)

    foi_message_factory(
        request=req,
        is_response=False,
        timestamp=datetime(2022, 1, 1, tzinfo=timezone.utc),
        plaintext=f"To whom it may concern\n\n{req_text}\n\nGreetings",
        plaintext_redacted=f"To whom it may concern\n\n{req_text}\n\nGreetings",
    )
    foi_message_factory(
        request=req,
        is_response=True,
        timestamp=datetime(2022, 1, 5, tzinfo=timezone.utc),
        plaintext="Some random response text",
        plaintext_redacted="Some random response text",
    )
    return req


@pytest.mark.django_db
@pytest.mark.parametrize(
    "req_fixture", ["req_with_ordered_messages", "req_with_unordered_messages"]
)
def test_message_highlight(client: Client, req_fixture: str, request):
    """
    Test that highlighting works (even if the message with the request content is not the first message)
    """
    req = request.getfixturevalue(req_fixture)
    response = client.get(req.get_absolute_url())
    assert response.status_code == 200
    content = response.content.decode()
    assert req.description in content

    assertInHTML(
        f'<div class="highlight">{req.description}</div>',
        content,
    )


@pytest.fixture
def jurisdiction_with_many_requests(world):
    site = world
    user = User.objects.first()
    jurisdiction = Jurisdiction.objects.first()
    for _ in range(40):
        law = FoiLaw.objects.filter(site=site, jurisdiction=jurisdiction).first()
        public_body = PublicBody.objects.filter(jurisdiction=jurisdiction).first()
        req = factories.FoiRequestFactory.create(
            site=site,
            user=user,
            resolution="successful",
            jurisdiction=jurisdiction,
            law=law,
            public_body=public_body,
        )
        factories.FoiMessageFactory.create(
            request=req, sender_user=user, recipient_public_body=public_body
        )
        mes = factories.FoiMessageFactory.create(
            request=req, sender_public_body=public_body
        )
        factories.FoiAttachmentFactory.create(belongs_to=mes, approved=False)
        factories.FoiAttachmentFactory.create(belongs_to=mes, approved=True)
    return jurisdiction


def jurisdiction_with_many_requests_slug(request: pytest.FixtureRequest):
    return request.getfixturevalue("jurisdiction_with_many_requests").slug


@pytest.mark.django_db
@pytest.mark.parametrize(
    "filter_field,filter_value,filter_value_function",
    [["jurisdiction", None, jurisdiction_with_many_requests_slug], ["q", "*", None]],
)
@pytest.mark.usefixtures(
    "jurisdiction_with_many_requests"
)  # We always need enough requests to have a second page we can filter for
def test_request_list_filter_pagination(
    request: pytest.FixtureRequest,
    client,
    filter_field: str,
    filter_value: Optional[str],
    filter_value_function: Optional[Callable],
):
    if filter_value is None and filter_value_function is not None:
        filter_value = filter_value_function(request)

    factories.rebuild_index()

    list_url = (
        reverse(
            "foirequest-list",
        )
        + "?"
        + urllib.parse.urlencode({filter_field: filter_value})
    )
    response = client.get(list_url)
    assert response.status_code == 200

    saw_page_link = False
    soup = BeautifulSoup(response.content.decode(), "lxml")
    for link in soup.find_all("a", class_="page-link"):
        href = link.get("href")
        if href == "#":
            continue
        query = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        assert query.get(filter_field) == [filter_value]

        saw_page_link = True
        link_url = urllib.parse.urljoin(list_url, link.get("href"))

        response = client.get(link_url)
        assert response.status_code == 200

    assert saw_page_link


def dict_combinations_all_r(sequence):
    for r in range(len(sequence) + 1):
        for parts in itertools.combinations(sequence, r=r):
            yield dict(parts)


@pytest.mark.django_db
def test_request_list_path_filter(
    client: Client,
    jurisdiction_with_many_requests: Jurisdiction,
):
    factories.rebuild_index()

    kwargs_elements = [
        ("jurisdiction", jurisdiction_with_many_requests.slug),
        ("status", "successful"),
    ]

    query_elements = [("q", "*"), ("sort", "last")]

    for kwargs in dict_combinations_all_r(kwargs_elements):
        qe = query_elements + [x for x in kwargs_elements if x[0] not in kwargs]
        for query in dict_combinations_all_r(qe):
            list_url = (
                reverse("foirequest-list", kwargs=kwargs)
                + "?"
                + urllib.parse.urlencode(query)
            )
            response = client.get(list_url)
            assert response.status_code == 200

            saw_page_link = False
            soup = BeautifulSoup(response.content.decode(), "lxml")
            for link in soup.find_all("a", class_="page-link"):
                href = link.get("href")
                if href == "#":
                    continue
                target_url = urllib.parse.urljoin(list_url, href)
                target_path = urllib.parse.urlparse(target_url).path
                target_resolved = resolve(target_path)
                # Pagination should link to a foirequest-list again
                assert target_resolved.url_name == "foirequest-list"
                target_query = urllib.parse.parse_qs(
                    urllib.parse.urlparse(target_url).query
                )

                # Query filters and filters set via the path should not overlap
                assert not (target_query.keys() & target_resolved.kwargs.keys())
                for k, v in itertools.chain(kwargs.items(), query.items()):
                    assert k in target_query or k in target_resolved.kwargs
                    assert (
                        target_query.get(k) == [v] or target_resolved.kwargs.get(k) == v
                    )

                saw_page_link = True

                response = client.get(target_url)
                assert response.status_code == 200

            assert saw_page_link
