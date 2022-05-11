import json
from typing import Any, Dict, List, Optional, Union

from django.db import models
from django.forms.fields import Field
from django.forms.utils import ErrorList
from django.utils.safestring import SafeString

from rest_framework.utils.serializer_helpers import ReturnDict

from froide.publicbody.models import PublicBody


class DjangoJSONEncoder(json.JSONEncoder):
    def default(self, obj: PublicBody) -> ReturnDict:
        if isinstance(obj, models.Model) and hasattr(obj, "as_data"):
            return obj.as_data()
        if isinstance(obj, models.query.QuerySet):
            return json.JSONEncoder.default(self, [x for x in obj])
        return json.JSONEncoder.default(self, obj)


Data = Union[List[Dict[str, str]], str]


def get_data(error: Union[ErrorList, str]) -> Data:
    if isinstance(error, (dict, str)):
        return error
    return error.get_json_data()


FieldDict = Dict[str, Optional[Union[str, bool, SafeString, int]]]


class JSONMixin(object):
    def as_json(self) -> str:
        return json.dumps(self.as_data(), cls=DjangoJSONEncoder)

    def as_data(self) -> Dict[str, Any]:
        return {
            "fields": {
                str(name): self.field_to_dict(name, field)
                for name, field in self.fields.items()
            },
            "errors": {f: get_data(e) for f, e in self.errors.items()},
            "nonFieldErrors": [get_data(e) for e in self.non_field_errors()],
        }

    def field_to_dict(self, name: str, field: Field) -> FieldDict:
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
        }
