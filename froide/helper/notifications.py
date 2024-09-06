import datetime
from dataclasses import dataclass
from typing import Optional, Protocol


class Event(Protocol):
    def as_text(self) -> str: ...

    def as_html(self) -> str: ...


class TemplatedEvent(Event):
    def __init__(self, template, template_html="", **context):
        self.template = template
        self.template_html = template_html
        self.context = context

    def as_text(self):
        return self.template.format(**self.context)

    def as_html(self):
        return self.template_html.format(**self.context)


@dataclass
class Notification:
    section: str
    event_type: str
    object: any
    object_label: str
    timestamp: datetime.datetime
    event: Event
    user_id: Optional[int]
