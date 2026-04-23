from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext as _
from django.utils.translation import ngettext


@dataclass
class AlertEvent:
    title: str
    url: str
    content: str

    def as_text(self):
        return f"""{self.title}
<{self.url}>"""

    def as_html(self):
        return format_html(
            """<h4>{} (<a href="{}">{}</a>)</h4>
<p>{}</p>""",
            self.url,
            self.title,
            _("search results"),
            self.content,
        )


@dataclass
class AlertSection:
    key: str
    title: str
    url: str
    results: list[AlertEvent]
    result_count: int

    def as_text(self):
        if self.result_count == 0:
            return ""
        more_text = ""
        if self.result_count > len(self.results):
            more_count = self.result_count - len(self.results)
            more_text = "\n" + ngettext(
                "There is one more result.",
                "There are %(count)s more results.",
                more_count,
            ) % {"count": more_count}
        result_text = "\n\n".join(result.as_text() for result in self.results)
        return f"""# {self.title}
<{self.url}>

{result_text}
{more_text}"""

    def as_html(self):
        if self.result_count == 0:
            return ""
        more_html = ""
        if self.result_count > len(self.results):
            more_count = self.result_count - len(self.results)
            more_html = format_html(
                '<p><a href="{}">{}</a></p>',
                self.url,
                ngettext(
                    "There is one more result.",
                    "There are %(count)s more results.",
                    more_count,
                )
                % {"count": more_count},
            )
        return format_html(
            """<h3><a href="{}">{}</a></h3>
{}
{}""",
            self.url,
            self.title,
            mark_safe("\n".join(e.as_html() for e in self.results)),
            more_html,
        )


class AlertConfiguration:
    key: str
    title: str = ""

    def search(
        self, query: str, start_date: datetime, user=None
    ) -> tuple[int, list[AlertEvent]]: ...

    def get_search_link(self, query: str, start_date: datetime) -> str: ...


class AlertRegistry:
    def __init__(self):
        self.entries: dict[str, AlertConfiguration] = {}

    def register(self, configuration: AlertConfiguration):
        if configuration.key in self.entries:
            raise ValueError(
                "%s registered twice with alert registry!" % configuration.slug
            )

        self.entries[configuration.key] = configuration
        return configuration

    def get_choices(self) -> list[tuple[str, str]]:
        return [(key, entry.title) for key, entry in self.entries.items()]

    def get_entries(self) -> Iterable[AlertConfiguration]:
        yield from self.entries.values()

    def get_keys(self) -> list[str]:
        return list(self.entries.keys())

    def get_for_keys(self, keys: Iterable[str]) -> Iterable[AlertConfiguration]:
        keys = set(keys)
        for entry_key in self.entries:
            if entry_key not in keys:
                continue
            yield self.entries[entry_key]


alert_registry = AlertRegistry()
