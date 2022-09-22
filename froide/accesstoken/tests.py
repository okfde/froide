import uuid
from datetime import datetime

import pytest

from froide.accesstoken.models import AccessToken, AccessTokenManager
from froide.account.models import User

PURPOSE = "test_purpose"
AT_MANAGER = AccessTokenManager()


@pytest.mark.django_db
def test_create_for_user(user):
    accesstoken = AT_MANAGER.create_for_user(user, PURPOSE)
    assert isinstance(accesstoken, uuid.UUID)


@pytest.mark.django_db
def test_reset(user):
    old_token = AT_MANAGER.create_for_user(user, PURPOSE)
    new_token = AT_MANAGER.reset(user, PURPOSE)
    assert not old_token == new_token
    assert isinstance(new_token, uuid.UUID)


@pytest.mark.django_db
def test_get_token_by_user(user):
    accesstoken = AT_MANAGER.create_for_user(user, PURPOSE)
    received_token = AT_MANAGER.get_token_by_user(user, PURPOSE)
    assert accesstoken == received_token


@pytest.mark.django_db
def test_get_by_user(user):
    ret_value = AT_MANAGER.get_by_user(user, PURPOSE)
    assert ret_value is None
    AccessToken.objects.create_for_user(user, PURPOSE)
    ret_value = AccessToken.objects.get_by_user(user, PURPOSE)
    assert isinstance(ret_value, AccessToken)


@pytest.mark.django_db
def test_get_by_token(user):
    at = AccessToken()
    ret_value = AT_MANAGER.get_by_token(at.token, PURPOSE)
    assert ret_value is None
    accesstoken = AT_MANAGER.create_for_user(user, PURPOSE)
    ret_value = AT_MANAGER.get_by_token(accesstoken, PURPOSE)
    assert isinstance(ret_value, AccessToken)


# Check if correct user is returned
@pytest.mark.django_db
def test_get_user_by_token(user):
    accesstoken = AT_MANAGER.create_for_user(user, PURPOSE)
    received_user = AT_MANAGER.get_user_by_token(accesstoken, PURPOSE)
    assert user == received_user


@pytest.mark.django_db
def test_constructor(user):
    AT_MANAGER.create_for_user(user, PURPOSE)
    accesstoken = AT_MANAGER.get_by_user(user, PURPOSE)
    assert isinstance(accesstoken.token, uuid.UUID)
    assert isinstance(accesstoken.purpose, str)
    assert isinstance(accesstoken.user, User)
    assert isinstance(accesstoken.timestamp, datetime)
    assert accesstoken.user is not None
    assert accesstoken.purpose is not None
