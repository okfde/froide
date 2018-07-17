import json

from django import forms
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.contrib.staticfiles.templatetags.staticfiles import static

from froide.helper.content_urls import get_content_url

from .models import PublicBody


def get_widget_context():
    return {
        'url': {
            'searchPublicBody': reverse('api:publicbody-search'),
            'getPublicBody': reverse('api:publicbody-detail', kwargs={'pk': '0'}),
            'helpAbout': get_content_url('about')
        },
        'i18n': {
            'missingPublicBody': _('Are we missing a public body?'),
            'publicBodySearchPlaceholder': _('Ministry of...'),
            'search': _('Search'),
            'examples': _('Examples:'),
            'environment': _('Environment'),
            'ministryOfLabour': _('Ministry of Labour'),
            'or': _('or'),
            'noPublicBodiesFound': _('No Public Bodies found for this query.'),
            'letUsKnow': _('Please let us know!'),
        },
        'resources': {
            'spinner': static('img/spinner.gif')
        }
    }


class PublicBodySelect(forms.Widget):
    input_type = "text"
    template_name = 'publicbody/_chooser.html'
    initial_search = None

    class Media:
        extend = False
        js = ('js/publicbody.js',)

    def set_initial_search(self, search):
        self.initial_search = search

    def get_context(self, name, value=None, attrs=None):
        pb, pb_desc = None, None
        if value is not None:
            try:
                pb = PublicBody.objects.get(pk=int(value))
                pb_desc = pb.get_label()
            except (ValueError, PublicBody.DoesNotExist):
                pass
        context = super(PublicBodySelect, self).get_context(name, value, attrs)
        context['widget'].update({
            'value_label': pb_desc,
            'search': self.initial_search,
            'publicbody': pb,
            'json': json.dumps({
                'fields': {
                    name: {
                        'value': value,
                        'objects': [pb.as_data()] if pb is not None else None
                    }
                }
            })
        })
        context['config'] = json.dumps(get_widget_context())
        return context
