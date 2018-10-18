from django import forms

from django_filters.widgets import RangeWidget


class DropDownFilterWidget(forms.widgets.ChoiceWidget):
    template_name = 'foirequest/widgets/dropdown_filter.html'

    def __init__(self, *args, **kwargs):
        self.get_url = kwargs.pop('get_url', None)
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        value = super(DropDownFilterWidget, self).render(name, value, attrs=attrs, renderer=renderer)
        return value

    def get_context(self, name, value, attrs):
        self.default_label = self.attrs.get('label', '')
        self.selected_label = self.default_label
        context = super(DropDownFilterWidget, self).get_context(
            name, value, attrs
        )
        context['selected_label'] = self.selected_label
        context['default_label'] = self.default_label
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
        option['url'] = self.get_url(data)
        return option


class AttachmentFileWidget(forms.ClearableFileInput):
    template_name = 'foirequest/widgets/attachment_file.html'


class DateRangeWidget(RangeWidget):
    template_name = 'foirequest/widgets/daterange.html'

    def __init__(self):
        widgets = [
            forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
        ]
        super(RangeWidget, self).__init__(widgets)
