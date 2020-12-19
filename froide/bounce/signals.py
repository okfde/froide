from django.dispatch import Signal

user_email_bounced = Signal()  # args: ['bounce', 'should_deactivate']
email_bounced = Signal()  # args: ['bounce', 'should_deactivate']

email_unsubscribed = Signal()  # args: ['email', 'reference']
