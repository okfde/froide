from datetime import datetime, timezone

from django.contrib.auth import get_user_model

import factory
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()

    first_name = "Jane"
    last_name = factory.Sequence(lambda n: "D%se" % ("o" * min(20, int(n))))
    username = factory.Sequence(lambda n: "user_%s" % n)
    email = factory.Sequence(lambda n: "user%s@example.org" % n)
    password = factory.PostGenerationMethodCall("set_password", "froide")
    is_staff = False
    is_active = True
    is_superuser = False
    last_login = datetime(2000, 1, 1).replace(tzinfo=timezone.utc)
    date_joined = datetime(1999, 1, 1).replace(tzinfo=timezone.utc)
    private = False
    address = "Dummystreet5\n12345 Town"
    organization_name = ""
    organization_url = ""
