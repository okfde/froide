from collections import defaultdict

from django.contrib.auth import get_user_model

User = get_user_model()


class UserExtrasRegistry:
    def __init__(self):
        self.registry = defaultdict(list)

    def register(self, key, form_extender):
        self.registry[key].append(form_extender)

    def on_init(self, key: str, form) -> None:
        for fe in self.registry[key]:
            fe.on_init(form)

    def on_clean(self, key: str, form) -> None:
        for fe in self.registry[key]:
            fe.on_clean(form)

    def on_save(self, key: str, form, user: User) -> None:
        for fe in self.registry[key]:
            fe.on_save(form, user)


user_extra_registry = UserExtrasRegistry()
