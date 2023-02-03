from django.dispatch import Signal

account_confirmed = Signal()  # args: ['request']
account_canceled = Signal()  # args: ['user']
account_activated = Signal()  # args: ['user']
account_email_changed = Signal()  # args: ['old_email']
account_made_private = Signal()  # args: ['user']
account_merged = Signal()  # args: ['old_user', 'new_user']
account_future_canceled = Signal()
