import json


def field_to_dict(form, name, field):
    return {
        "type": field.__class__.__name__,
        "widget_type": field.widget.__class__.__name__,
        "hidden": field.widget.is_hidden,
        "required": field.widget.is_required,
        "label": str(field.label),
        "help_text": str(field.help_text),
        "initial": field.initial,
        "placeholder": str(field.widget.attrs.get('placeholder', '')),
        "value": form[name].value() if form.is_bound else None
    }


class JSONMixin(object):
    def as_json(self):
        return json.dumps({
            'fields': {
                str(name): field_to_dict(self, name, field) for name, field in self.fields.items()
            },
            'errors': {f: e.get_json_data() for f, e in self.errors.items()},
            'nonFieldErrors': [e.get_json_data() for e in self.non_field_errors()]
        })
