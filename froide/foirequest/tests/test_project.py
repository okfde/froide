from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import mail
from django.test import TestCase
from django.urls import reverse

import pytest

from froide.account.factories import UserFactory
from froide.foirequest.forms.project import AssignProjectForm
from froide.foirequest.models import FoiProject, FoiRequest
from froide.foirequest.models.message import FoiMessage
from froide.foirequest.tasks import create_project_messages, create_project_requests
from froide.foirequest.tests import factories
from froide.helper.db_utils import save_obj_with_slug
from froide.publicbody.models import PublicBody

User = get_user_model()


class RequestProjectTest(TestCase):
    def setUp(self):
        factories.make_world()
        self.pb1 = PublicBody.objects.filter(jurisdiction__slug="bund")[0]
        self.pb2 = PublicBody.objects.filter(jurisdiction__slug="nrw")[0]
        ct = ContentType.objects.get_for_model(FoiRequest)
        self.perm = Permission.objects.get(content_type=ct, codename="create_batch")

    def test_create_project(self):
        user = User.objects.get(email="info@fragdenstaat.de")
        user.user_permissions.add(self.perm)

        ok = self.client.login(email=user.email, password="froide")
        self.assertTrue(ok)

        pb_ids = "%s+%s" % (self.pb1.pk, self.pb2.pk)
        response = self.client.get(
            reverse("foirequest-make_request", kwargs={"publicbody_ids": pb_ids})
        )
        self.assertEqual(response.status_code, 200)
        data = {
            "subject": "Test-Subject",
            "body": "This is another test body with Ümläut€n",
            "public": True,
            "publicbody": pb_ids.split("+"),
        }
        mail.outbox = []
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("foirequest-make_request"), data)
        self.assertEqual(response.status_code, 302)
        project = FoiProject.objects.get(title=data["subject"])
        self.assertEqual(
            {str(x.pk) for x in project.publicbodies.all()}, set(pb_ids.split("+"))
        )
        request_sent = reverse("foirequest-request_sent") + "?project=%s" % project.pk
        self.assertEqual(response["Location"], request_sent)
        self.assertEqual(project.title, data["subject"])
        self.assertEqual(project.description, data["body"])
        self.assertEqual(project.foirequest_set.all().count(), 2)
        self.assertEqual(len(mail.outbox), 3)  # 2 to pb, one to user
        requests = project.foirequest_set.all()
        first_message_1 = requests[0].messages[0]
        first_message_2 = requests[1].messages[0]
        self.assertNotEqual(first_message_1.plaintext, data["body"])
        last_part_1 = first_message_1.plaintext.split(data["body"])[1]
        last_part_2 = first_message_2.plaintext.split(data["body"])[1]
        self.assertNotEqual(last_part_1, last_part_2)

        response = self.client.get(
            reverse("foirequest-project_shortlink", kwargs={"obj_id": project.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_create_project_full_text(self):
        user = User.objects.get(email="info@fragdenstaat.de")
        user.user_permissions.add(self.perm)

        ok = self.client.login(email=user.email, password="froide")
        self.assertTrue(ok)

        pb_ids = (self.pb1.pk, self.pb2.pk)
        data = {
            "subject": "Test-Subject",
            "body": "This is another test body with Ümläut€n",
            "public": True,
            "publicbody": pb_ids,
            "full_text": "on",
        }
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("foirequest-make_request"), data)
        self.assertEqual(response.status_code, 302)
        project = FoiProject.objects.get(title=data["subject"])
        requests = project.foirequest_set.all()
        first_message_1 = requests[0].messages[0]
        first_message_2 = requests[1].messages[0]
        self.assertTrue(first_message_1.plaintext.startswith(data["body"]))
        self.assertTrue(first_message_2.plaintext.startswith(data["body"]))

    def test_draft_project(self):
        """
        A non-batch user can be assigned a batch draft
        The user cannot change the public bodies, but is able to sent
        the request.
        """
        user = User.objects.get(email="dummy@example.org")

        old_project = factories.FoiProjectFactory(user=user)

        ok = self.client.login(email=user.email, password="froide")
        self.assertTrue(ok)
        draft = factories.RequestDraftFactory.create(user=user)
        draft.publicbodies.add(self.pb1, self.pb2)

        evil_pb3 = PublicBody.objects.filter(jurisdiction__slug="nrw")[1]
        pb_ids = [self.pb1.pk, self.pb2.pk]
        response = self.client.get(draft.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        mail.outbox = []

        draft.project = old_project
        draft.save()

        data = {
            "subject": "Test-Subject",
            "body": "This is another test body with Ümläut€n",
            "public": True,
            "publicbody": pb_ids + [evil_pb3],
            "draft": draft.pk,
        }

        request_url = reverse("foirequest-make_request")
        response = self.client.post(request_url, data)
        self.assertContains(response, "Draft cannot be used again", status_code=400)

        draft.project = None
        draft.save()

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(request_url, data)
        self.assertEqual(response.status_code, 302)

        project = FoiProject.objects.get(title=data["subject"])
        self.assertEqual(set(pb_ids), {x.id for x in project.publicbodies.all()})
        self.assertEqual(len(mail.outbox), 3)  # two pbs, one user to user


@pytest.fixture
def project_with_requests(world, user, faker) -> FoiProject:
    data = {
        "subject": faker.text(max_nb_chars=50),
        "body": faker.text(max_nb_chars=500),
        "publicbodies": list(PublicBody.objects.all()[:10]),
    }

    project = FoiProject.objects.create(
        title=data["subject"],
        description=data["body"],
        status=FoiProject.STATUS_READY,
        user=user,
        request_count=len(data["publicbodies"]),
        public=True,
        site=world,
    )

    save_obj_with_slug(project)
    project.save()

    create_project_requests(
        project.id,
        [x.id for x in data["publicbodies"]],
        subject=data["subject"],
        message=data["body"],
    )

    return project


@pytest.mark.django_db
def test_project_mass_mail(project_with_requests, faker):
    project_foireqs = project_with_requests.foirequest_set.all()
    assert project_foireqs.count() > 0

    subject = faker.text()
    message = faker.text()
    mail.outbox = []

    # Action: Send a message to all public bodies in the request
    create_project_messages(
        foirequest_ids=project_foireqs.values_list("id", flat=True),
        user_id=project_with_requests.user.id,
        subject=subject,
        message=message,
    )

    # Expectation: Messages are marked as bulk
    messages = FoiMessage.objects.filter(
        subject=subject, request__in=project_with_requests.foirequest_set.all()
    )
    for message in messages:
        assert message.is_bulk

    # Expectation: Messages are send out to all public bodies in the request
    # Expectation: The user is not notified of the sent messages
    assert len(mail.outbox) == project_foireqs.count()
    out_mails = {msg.to[0] for msg in mail.outbox}
    assert project_with_requests.user.email not in out_mails
    pb_mails = set(project_foireqs.values_list("public_body__email", flat=True))
    assert out_mails == pb_mails


def make_project(user, request_count):
    project = factories.FoiProjectFactory.create(
        user=user, site=Site.objects.get_current(), request_count=request_count
    )
    for order in range(request_count):
        req = factories.FoiRequestFactory.create(
            user=user, project=project, project_order=order
        )
        project.publicbodies.add(req.public_body)
    return project


def move_via_web_form(client, requests, project):
    for req in requests:
        req.refresh_from_db()
        form = AssignProjectForm(
            data={"project": project.id if project else ""},
            user=req.user,
            instance=req,
        )
        assert form.is_valid(), form.errors
        form.save()


def login_staff_user(client, permission):
    user = UserFactory.create(is_staff=True)
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="foirequest", codename=permission
        )
    )
    client.force_login(user)


def move_via_admin_add_action(client, requests, project):
    login_staff_user(client, "change_foirequest")
    url = reverse("admin:foirequest_foirequest_changelist")
    response = client.post(
        url,
        {
            "action": "add_to_project",
            "_selected_action": [req.id for req in requests],
            "obj": project.id,
        },
    )
    assert response.status_code == 302
    assert response.url == url


def move_via_admin_merge_action(client, requests, project):
    login_staff_user(client, "change_foiproject")
    url = reverse("admin:foirequest_foiproject_changelist")
    response = client.post(
        url,
        {
            "action": "move_requests",
            "_selected_action": list({req.project_id for req in requests}),
            "obj": project.id,
        },
    )
    assert response.status_code == 302
    assert response.url == url


def assert_project_consistent(project):
    project.refresh_from_db()
    requests = list(project.foirequest_set.order_by("project_order"))
    assert [req.project_order for req in requests] == list(range(len(requests)))
    assert project.request_count == len(requests)
    assert set(project.publicbodies.all()) == {req.public_body for req in requests}


def assert_moved_to_end(project, moved_requests):
    count = project.foirequest_set.count()
    for req in moved_requests:
        req.refresh_from_db()
        assert req.project == project
    assert {req.project_order for req in moved_requests} == set(
        range(count - len(moved_requests), count)
    )


@pytest.mark.django_db
@pytest.mark.parametrize("move", [move_via_web_form])
def test_move_request_to_other_project(user, client, move):
    old_project = make_project(user, 3)
    new_project = make_project(user, 3)
    req = old_project.foirequest_set.get(project_order=0)

    move(client, [req], new_project)

    assert_moved_to_end(new_project, [req])
    assert_project_consistent(old_project)
    assert_project_consistent(new_project)


@pytest.mark.django_db
@pytest.mark.parametrize("move", [move_via_web_form, move_via_admin_add_action])
def test_move_request_without_project_into_project(user, client, move):
    new_project = make_project(user, 3)
    req = factories.FoiRequestFactory.create(user=user)

    move(client, [req], new_project)

    assert_moved_to_end(new_project, [req])
    assert_project_consistent(new_project)


@pytest.mark.django_db
@pytest.mark.parametrize("move", [move_via_web_form, move_via_admin_merge_action])
def test_move_all_requests_to_other_project(user, client, move):
    old_project = make_project(user, 3)
    new_project = make_project(user, 3)
    requests = list(old_project.foirequest_set.all())

    move(client, requests, new_project)

    assert_moved_to_end(new_project, requests)
    assert_project_consistent(old_project)
    assert_project_consistent(new_project)


@pytest.mark.django_db
@pytest.mark.parametrize("move", [move_via_web_form])
def test_remove_request_from_project(user, client, move):
    old_project = make_project(user, 3)
    req = old_project.foirequest_set.get(project_order=0)

    move(client, [req], None)

    req.refresh_from_db()
    assert req.project is None
    assert req.project_order is None
    assert_project_consistent(old_project)


@pytest.mark.django_db
@pytest.mark.parametrize("move", [move_via_web_form])
def test_move_request_to_same_project_keeps_number(user, client, move):
    project = make_project(user, 3)
    req = project.foirequest_set.get(project_order=0)

    move(client, [req], project)

    req.refresh_from_db()
    assert req.project == project
    assert req.project_order == 0
    assert_project_consistent(project)


@pytest.mark.django_db
def test_project_numbers_start_at_one(user):
    project = make_project(user, 3)

    requests = project.foirequest_set.order_by("project_order")

    assert [req.project_number for req in requests] == [1, 2, 3]


@pytest.mark.django_db
def test_recalculate_order_keeps_older_request_first_for_duplicate_numbers(user):
    project = make_project(user, 0)
    # Insert the newer request first. Postgres usually returns fresh rows in
    # insertion order, so without a tiebreak newer would come before older.
    newer = factories.FoiRequestFactory.create(
        id=100002, user=user, project=project, project_order=0
    )
    older = factories.FoiRequestFactory.create(
        id=100001, user=user, project=project, project_order=0
    )

    project.recalculate_order()

    requests = project.foirequest_set.order_by("project_order")
    assert [req.id for req in requests] == [older.id, newer.id]


@pytest.mark.django_db
def test_update_publicbodies_removes_public_bodies_of_removed_requests(user):
    project = make_project(user, 3)
    req = project.foirequest_set.get(project_order=0)
    req.project = None
    req.save()

    project.update_publicbodies()

    assert req.public_body not in project.publicbodies.all()
    assert set(project.publicbodies.all()) == {
        remaining.public_body for remaining in project.foirequest_set.all()
    }
