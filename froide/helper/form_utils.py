import json
from decimal import Decimal

from django.db import models


class DjangoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, models.Model) and hasattr(obj, "as_data"):
            return obj.as_data()
        if isinstance(obj, models.query.QuerySet):
            return json.JSONEncoder.default(self, list(obj))
        return json.JSONEncoder.default(self, obj)


def get_data(error):
    if isinstance(error, (dict, str)):
        return error
    return error.get_json_data()


# FIXME WIP this is maybe not the smartest way to do this
# use simplejson instead?
def serialize_extra(obj):
    # FIXME: this is a hack to serialize some extra types
    # Publicbody should not be coupled to helper
    from froide.publicbody.models import PublicBody

    if isinstance(obj, Decimal):
        return {
            "__Decimal": True,
            "intValue": int(obj * 100),
            "strValue": str(obj),
        }
    if isinstance(obj, PublicBody):
        return {
            "__PublicBody": True,
            "id": obj.id,
            "name": obj.name,
            "jurisdiction": {"name": obj.jurisdiction.name},
        }
    raise TypeError


class JSONMixin(object):
    def as_json(self):
        return json.dumps(
            self.as_data(), default=serialize_extra, cls=DjangoJSONEncoder
        )

    def as_json_pretty(self):
        return json.dumps(
            self.as_data(), default=serialize_extra, cls=DjangoJSONEncoder, indent="  "
        )

    def as_data(self):
        return {
            "fields": {
                str(name): self.field_to_dict(name, field)
                for name, field in self.fields.items()
            },
            "errors": {f: get_data(e) for f, e in self.errors.items()},
            "nonFieldErrors": [get_data(e) for e in self.non_field_errors()],
        }

    def field_to_dict(self, name, field):
        choices = getattr(field, "choices", None)
        if choices and not field.widget.is_hidden:
            choices = [
                {
                    "value": str(c[0]),
                    "label": str(c[1]),
                }
                for c in choices
            ]
        else:
            choices = None
        return {
            "type": field.__class__.__name__,
            "widget_type": field.widget.__class__.__name__,
            "hidden": field.widget.is_hidden,
            "required": field.widget.is_required,
            "label": str(field.label),
            "help_text": str(field.help_text),
            "initial": self.get_initial_for_field(field, name),
            "placeholder": str(field.widget.attrs.get("placeholder", "")),
            "value": self[name].value() if self.is_bound else None,
            "choices": choices,
        }
