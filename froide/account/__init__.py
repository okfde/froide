from django.dispatch import Signal

default_app_config = 'froide.account.apps.AccountConfig'

account_canceled = Signal(providing_args=['user'])
