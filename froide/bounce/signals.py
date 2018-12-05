from django.dispatch import Signal

user_email_bounced = Signal(providing_args=["should_deactivate"])
email_bounced = Signal(providing_args=["should_deactivate"])
