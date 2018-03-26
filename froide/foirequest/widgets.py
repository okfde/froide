from django import forms
from django.utils.http import urlencode
from django.urls import reverse


def make_filter_url(data):
    from .filters import get_active_filters

    data = dict(data)
    url_kwargs = {}
    for key in get_active_filters(data):
        url_kwargs[key] = data.pop(key)

    query_string = ''
    data = {k: v for k, v in data.items() if v}
    if data:
        query_string = '?' + urlencode(data)
    return reverse('foirequest-list', kwargs=url_kwargs) + query_string


class DropDownFilterWidget(forms.widgets.ChoiceWidget):
    template_name = 'foirequest/widgets/dropdown_filter.html'

    def render(self, name, value, attrs=None, renderer=None):
        value = super(DropDownFilterWidget, self).render(name, value, attrs=attrs, renderer=renderer)
        return value

    def get_context(self, name, value, attrs):
        self.selected_label = self.attrs.get('label', '')
        context = super(DropDownFilterWidget, self).get_context(
            name, value, attrs
        )
        context['selected_label'] = self.selected_label
        return context

    def create_option(self, name, value, label, selected, index,
                      subindex=None, attrs=None):
        option = super(DropDownFilterWidget, self).create_option(name, value,
            label, selected, index, subindex=subindex, attrs=attrs)
        if selected and value:
            self.selected_label = label
        # Data is set on widget directly before rendering
        data = self.data.copy()
        data[name] = value
        option['url'] = make_filter_url(data)
        return option


class AttachmentFileWidget(forms.ClearableFileInput):
    template_name = 'foirequest/widgets/attachment_file.html'
