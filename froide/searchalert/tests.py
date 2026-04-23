from django.urls import reverse

import pytest

from froide.searchalert.updates import collect_updates, send_update

from .configuration import AlertConfiguration, AlertEvent, alert_registry
from .models import Alert


@pytest.mark.django_db
def test_subscribe_user(client, dummy_user):
    client.force_login(dummy_user)
    subscribe_url = reverse("searchalert:subscribe")
    response = client.post(
        subscribe_url,
        {"query": "test", "interval": "daily", "sections": ["foirequest"]},
    )
    assert response.status_code == 302

    alert = Alert.objects.get(user=dummy_user)
    assert alert.query == "test"
    assert alert.interval == "daily"
    assert alert.sections == {"foirequest": True}
    assert alert.email_confirmed is not None
    assert alert.email == ""
    assert alert.last_alert is not None


@pytest.mark.django_db
def test_subscribe_email(client, mailoutbox):
    subscribe_url = reverse("searchalert:subscribe")
    response = client.post(
        subscribe_url,
        {
            "email": "test@example.org",
            "query": "test",
            "interval": "daily",
            "sections": ["foirequest"],
        },
    )
    assert response.status_code == 302

    alert = Alert.objects.get(email="test@example.org")
    assert alert.query == "test"
    assert alert.interval == "daily"
    assert alert.sections == {"foirequest": True}
    assert alert.email_confirmed is None
    assert alert.last_alert is not None

    message = mailoutbox[0]
    subscribe_link = alert.get_subscribe_link()
    assert subscribe_link in message.body

    response = client.get(subscribe_link)
    assert response.status_code == 200
    alert.refresh_from_db()
    assert alert.email_confirmed is None

    response = client.post(subscribe_link)
    assert response.status_code == 302
    alert.refresh_from_db()
    assert alert.email_confirmed is not None


@pytest.mark.django_db
def test_change_alert(client):
    alert = Alert.objects.create(
        email="test@example.com", query="test", interval="daily"
    )
    change_url = alert.get_change_url()
    response = client.get(change_url)
    assert response.status_code == 200

    response = client.post(
        change_url, {"interval": "weekly", "query": "foobar", "sections": ["document"]}
    )
    assert response.status_code == 302
    alert.refresh_from_db()
    assert alert.query == "foobar"
    assert alert.interval == "weekly"
    assert alert.sections == {"document": True}


@pytest.mark.django_db
def test_change_alert_user(client, dummy_user):
    alert = Alert.objects.create(query="test", interval="daily", user=dummy_user)
    change_url = alert.get_change_url()
    response = client.get(change_url)
    assert response.status_code == 404

    client.force_login(dummy_user)
    response = client.get(change_url)
    assert response.status_code == 200

    response = client.post(
        change_url, {"interval": "nad", "query": "foobar", "sections": ["document"]}
    )
    assert response.status_code == 200
    assert response.context["form"].errors

    response = client.post(
        change_url, {"interval": "weekly", "query": "foobar", "sections": ["document"]}
    )
    assert response.status_code == 302
    alert.refresh_from_db()
    assert alert.query == "foobar"
    assert alert.interval == "weekly"
    assert alert.sections == {"document": True}


@pytest.mark.django_db
def test_unsubscribe_user(client, dummy_user):
    alert = Alert.objects.create(query="test", interval="daily", user=dummy_user)
    unsub_url = alert.get_unsubscribe_url()
    response = client.get(unsub_url)
    assert response.status_code == 404

    client.force_login(dummy_user)
    response = client.get(unsub_url)
    assert response.status_code == 200
    alert.refresh_from_db()

    response = client.post(unsub_url)
    assert response.status_code == 302

    with pytest.raises(Alert.DoesNotExist):
        alert.refresh_from_db()


@pytest.mark.django_db
def test_unsubscribe(client):
    alert = Alert.objects.create(
        query="test", interval="daily", email="test@example.com"
    )
    unsub_url = alert.get_unsubscribe_url()
    response = client.get(unsub_url)
    assert response.status_code == 200

    alert.refresh_from_db()

    response = client.post(unsub_url)
    assert response.status_code == 302

    with pytest.raises(Alert.DoesNotExist):
        alert.refresh_from_db()


@pytest.fixture
def alert_config():
    class FakeConfig(AlertConfiguration):
        key = "test"
        title = "FakeConfigTitle"

        def search(self, query, start_date):
            return (
                5,
                [
                    AlertEvent(title="Test1", url="http://example.org/1", content=""),
                    AlertEvent(title="Test2", url="http://example.org/2", content=""),
                    AlertEvent(title="Test3", url="http://example.org/3", content=""),
                ],
            )

        def get_search_link(self, query, start):
            return "http://search.example.org/"

    alert_registry.register(FakeConfig())
    yield
    alert_registry.entries.pop("test")


@pytest.mark.django_db
def test_collect_update(alert_config):

    results = list(collect_updates("query", None, []))
    assert len(results) == 0

    results = list(collect_updates("query", None, ["test"]))
    assert len(results) == 1
    result = results[0]
    assert result.key == "test"
    assert result.title == "FakeConfigTitle"
    assert result.url == "http://search.example.org/"
    assert result.result_count == 5
    assert len(result.results) == 3
    assert result.results[0].title == "Test1"
    assert result.results[0].url == "http://example.org/1"


@pytest.mark.django_db
def test_send_update(alert_config, mailoutbox):
    alert = Alert.objects.create(
        email="test@example.com",
        query="test",
        interval="daily",
        sections={"test": True},
    )
    send_update(alert)

    message = mailoutbox[0]
    results = list(collect_updates("query", None, ["test"]))
    assert len(results) == 1
    result = results[0]
    assert result.as_text() in message.body


@pytest.mark.django_db
def test_empty_update(alert_config, mailoutbox):
    alert = Alert.objects.create(
        email="test@example.com",
        query="test",
        interval="daily",
        sections={"other": True},
    )
    send_update(alert)

    assert len(mailoutbox) == 0
