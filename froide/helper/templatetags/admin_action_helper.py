from django import forms, template
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME

register = template.Library()


class ActionForm(forms.Form):
    action = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        actions = kwargs.pop("actions")
        obj_id = kwargs.pop("object_id")
        super().__init__(*args, **kwargs)
        self.fields["action"].choices = actions
        self.fields[ACTION_CHECKBOX_NAME] = forms.CharField(widget=forms.HiddenInput)
        self.fields[ACTION_CHECKBOX_NAME].initial = obj_id


@register.simple_tag(takes_context=True)
def render_admin_action_form(context, model_admin, obj):
    request = context["request"]
    choices = model_admin.get_action_choices(request)
    if len(choices) < 3:  # ignore blank choice and default delete action
        return
    form = ActionForm(object_id=obj.id, actions=choices)
    return form
