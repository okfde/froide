from django.conf.urls.defaults import patterns
from django.conf import settings
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView

LG = settings.LANGUAGE_CODE

def TV(template):
    return TemplateView.as_view(template_name=template)

urlpatterns = patterns("",
    (r'^$', TV("help/%s/index.html" % LG), {}, 'help-index'),
    # Translators: URL part of /help/
    (r'^%s/$' % _('about'), TV("help/%s/about.html" % LG), {}, 'help-about'),
)
