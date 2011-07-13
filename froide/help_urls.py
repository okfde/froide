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
    # Translators: URL part of /help/
    (r'^%s/$' % _('terms'), TV("help/%s/terms.html" % LG), {}, 'help-terms'),
    # Translators: URL part of /help/
    (r'^%s/$' % _('privacy'), TV("help/%s/privacy.html" % LG), {}, 'help-privacy'),
    (r'^%s/$' % _('asking-questions'), TV("help/%s/asking-questions.html" % LG), {}, 'help-asking_questions'),

)
