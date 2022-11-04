import unittest
from unittest import mock

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse

import pytest
from pytest_django.asserts import (
    assertContains,
    assertNotContains,
    assertNumQueries,
    assertRedirects,
)

from froide.foirequest.filters import FOIREQUEST_FILTER_DICT, FOIREQUEST_FILTERS
from froide.foirequest.models import FoiAttachment, FoiRequest
from froide.foirequest.tests import factories
from froide.helper.search.signal_processor import realtime_search
from froide.publicbody.models import Category, Jurisdiction, PublicBody

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
    for urlpart in FOIREQUEST_FILTER_DICT:
        response = client.get(
            reverse("foirequest-list", kwargs={"status": str(urlpart)})
        )
        assert response.status_code == 200

    for topic in Category.objects.filter(is_topic=True):
        response = client.get(
            reverse("foirequest-list", kwargs={"category": topic.slug})
        )
        assert response.status_code == 200

    response = client.get(reverse("foirequest-list") + "?page=99999")
    assert response.status_code == 404


@pytest.mark.django_db
def test_list_jurisdiction_requests(world, client):
    factories.rebuild_index()
    juris = Jurisdiction.objects.all()[0]
    response = client.get(
        reverse("foirequest-list"), kwargs={"jurisdiction": juris.slug}
    )
    assert response.status_code == 200
    for urlpart in FOIREQUEST_FILTER_DICT:
        response = client.get(
            reverse(
                "foirequest-list",
                kwargs={"status": urlpart, "jurisdiction": juris.slug},
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

    status = FOIREQUEST_FILTERS[0][0]
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
