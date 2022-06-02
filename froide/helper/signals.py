from django.dispatch import Signal

email_left_queue = Signal()  # args: ['to', 'from', 'message_id', 'status', 'log']
