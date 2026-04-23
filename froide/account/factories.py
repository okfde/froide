from datetime import datetime, timezone

from django.contrib.auth import get_user_model

import factory
from factory.django import DjangoModelFactory

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    first_name = "Jane"
    last_name = factory.Sequence(lambda n: "D%se" % ("o" * min(20, int(n))))
    username = factory.Sequence(lambda n: "user_%s" % n)
    email = factory.Sequence(lambda n: "user%s@example.org" % n)
    is_staff = False
    is_active = True
    is_superuser = False
    last_login = datetime(2000, 1, 1).replace(tzinfo=timezone.utc)
    date_joined = datetime(1999, 1, 1).replace(tzinfo=timezone.utc)
    private = False
    address = "Dummystreet5\n12345 Town"
    organization_name = ""
    organization_url = ""

    @factory.post_generation
    def set_password(instance: User, create: bool, extracted, **kwargs):
        if create:
            instance.set_password("froide")
            instance.save()
