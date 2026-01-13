from django.utils.safestring import SafeString

import pytest

from froide.helper.search.queryset import ESQuerySetWrapper


class DummyHitMeta:
    def __init__(self, id, highlight=None):
        self.id = id
        self.highlight = highlight or {}


class DummyHit:
    def __init__(self, id, highlight=None):
        self.meta = DummyHitMeta(id, highlight)


class DummyObj:
    def __init__(self, pk):
        self.pk = pk
        self.query_highlight = None


class DummyQS:
    def __init__(self, objs):
        self._objs = objs

    def __iter__(self):
        return iter(self._objs)


# List of test cases to be used in the parameterized test below.
# Each test case is a tuple of (highlight_list, query_highlight) where highlight_list is the list
# of highlighted strings from Elasticsearch and expected_query_highlight is the expected post-processed
# string that will be shown to the user.
test_cases = [
    (
        [
            "Unterlagen zum &amp;quot;<em>Gender</em>-Verbot&amp;quot;\n\nAlle Unterlagen (interne und externe Korrespondenz, Vermerke",
            ", Dienstanweisungen etc.) im Zusammenhang mit dem sogenannten &amp;quot;<em>Gender</em>-Verbot&amp;quot; an sächsischen",
            "Schulen\n\nAnfrage erfolgreich \n\n\n\n\n    \n    Unterlagen zum &amp;quot;<em>Gender</em>-Verbot&amp;quot; [#284078]\n    Antrag",
            "externe Korrespondenz, Vermerke, Dienstanweisungen etc.) im Zusammenhang mit dem sogenannten &amp;quot;<em>Gender</em>-Verbot",
        ],
        (
            "Unterlagen zum &quot;<em>Gender</em>-Verbot&quot; [...] "
            ", Dienstanweisungen etc.) im Zusammenhang mit dem sogenannten &quot;<em>Gender</em>-Verbot&quot; an sächsischen [...] "
            # "Unterlagen zum &quot;<em>Gender</em>-Verbot&quot; [#284078] [...] "
            "externe Korrespondenz, Vermerke, Dienstanweisungen etc.) im Zusammenhang mit dem sogenannten &quot;<em>Gender</em>-Verbot"
        ),
    ),
    (
        [
            "Genderverbot\n\nDie Regelung (Schreiben, Erlass, Weisung) des BMF zur internen Sprachregelung in Bezug aufs <em>Gendern</em>",
            "zu:\n\nDie Regelung (Schreiben, Erlass, Weisung) des BMF zur internen Sprachregelung in Bezug aufs <em>Gendern</em>",
        ],
        "Die Regelung (Schreiben, Erlass, Weisung) des BMF zur internen Sprachregelung in Bezug aufs <em>Gendern</em>",
    ),
    (
        [
            "SIS II [#279515] # IFG-780&#x2F;005 II#1095\n    Der Bundesbeauftragte für den Datenschutz\nund die <em>Informationsfreiheit</em>",
            "SIS II [#279515] # IFG-780&#x2F;005 II#1095\n    Der Bundesbeauftragte für den Datenschutz\nund die <em>Informationsfreiheit</em>",
            "SIS II [#279515] # IFG-780&#x2F;005 II#1095\n    Der Bundesbeauftragte für den Datenschutz und die <em>Informationsfreiheit</em>",
            "SIS II [#279515] # IFG-780&#x2F;005 II#1095\n    Der Bundesbeauftragte für den Datenschutz und die <em>Informationsfreiheit</em>",
            "SIS II [#279515] # IFG-780&#x2F;005 II#1095\n    Der Bundesbeauftragte für den Datenschutz und die <em>Informationsfreiheit</em>",
            "SIS II [#279515] # IFG-780&#x2F;005 II#1095\n    Der Bundesbeauftragte für den Datenschutz und die <em>Informationsfreiheit</em>",
            "melek-bazgan-bfdi-12-12-2023.pdf\n      \n    \n\n\nDie Bundesbeauftragte für den Datenschutz und die <em>Informationsfreiheit</em>",
            "Beauftragte für Datenschutz und <em>Informationsfreiheit</em>\n\n\n    Datenschutz\n\n    <em>Informationsfreiheit</em>",
        ],
        (
            "Der Bundesbeauftragte für den Datenschutz\nund die <em>Informationsfreiheit</em> [...] "
            # "Die Bundesbeauftragte für den Datenschutz und die <em>Informationsfreiheit</em> [...] "
            "Beauftragte für Datenschutz und <em>Informationsfreiheit</em>"
            # "<em>Informationsfreiheit</em>"
        ),
    ),
    (
        [
            ":&#x2F;&#x2F;fragdenstaat.de&#x2F;hilfe&#x2F;fuer-behoerden&#x2F;\n\n      \n    \n\n    \n    Ihre Beschwerde im Bereich <em>Informationsfreiheit</em>",
            "Der Landesbeauftragte für den Datenschutz\nund die <em>Informationsfreiheit</em> Rheinland-Pfalz\n\nInternet",
            "Zeichen:\tfragdenstaat.de # 186145\n\n\n&amp;lt;&amp;lt;E-Mail-Adresse&amp;gt;&amp;gt;\n\n\nIhre Beschwerde im Bereich <em>Informationsfreiheit</em>",
            "Sie darauf hinweisen, dass die Anrufung des Landesbeauftragten für den Datenschutz und die <em>Informationsfreiheit</em>",
            "Slfdiprn0220071607220.pdf\n      \n    \n\n    \n    Ihre Beschwerde im Bereich <em>Informationsfreiheit</em>",
            "Der Landesbeauftragte für den Datenschutz\nund die <em>Informationsfreiheit</em> Rheinland-Pfalz\n\nInternet",
            "Zeichen:\tfragdenstaat.de # 186145\n\n\n&amp;lt;&amp;lt;E-Mail-Adresse&amp;gt;&amp;gt;\n\n\nIhre Beschwerde im Bereich <em>Informationsfreiheit</em>",
            "Mit freundlichen Grüßen\n      \n    \n\n    \n    AW: Ihre Beschwerde im Bereich <em>Informationsfreiheit</em> [#186145",
            "Ihr Antrag auf Informationszugang\n    Der Landesbeauftragte für den Datenschutz\nund die <em>Informationsfreiheit</em>",
            "Der Widerspruch ist bei dem Landesbeauftragten für den Datenschutz und die <em>Informationsfreiheit</em> Rheinland-Pfalz",
        ],
        (
            "Ihre Beschwerde im Bereich <em>Informationsfreiheit</em> [...] "
            "Der Landesbeauftragte für den Datenschutz\nund die <em>Informationsfreiheit</em> Rheinland-Pfalz [...] "
            "Sie darauf hinweisen, dass die Anrufung des Landesbeauftragten für den Datenschutz und die <em>Informationsfreiheit</em> [...] "
            "AW: Ihre Beschwerde im Bereich <em>Informationsfreiheit</em> [#186145 [...] "
            "Der Widerspruch ist bei dem Landesbeauftragten für den Datenschutz und die <em>Informationsfreiheit</em> Rheinland-Pfalz"
        ),
    ),
    (
        [
            "]\n    HmbTG Antrag auf Übersendung der beim Hamburgischen Beauftragten für Datenschutz und <em>Informationsfreiheit</em>",
            "Die Prüfung auf Übersendung der beim Hamburgischen Beauftragten für Datenschutz und <em>Informationsfreiheit</em>",
            "Ihrer Mail vom 02.02.2017 auf Zugang zu der dem Hamburgischen Beauftragten für Datenschutz und <em>Informationsfreiheit</em>",
            "Hintergrund war Ihr Antrag auf Zugang zu der dem Harnburgischen Beauftragten für Datenschutz und <em>Informationsfreiheit</em>",
            "Monats nach Bekanntgabe Widerspruch bei dem Harnburgischen Beauftragten für Datenschutz und <em>Informationsfreiheit</em>",
            "Möglichkeit, Widerspruch zu erheben - den Harnburgischen Beauftragten für Datenschutz und <em>Informationsfreiheit</em>",
            "hmbfdi-eao.pdf\n      \n    \n\n\nDer Hamburgische Beauftragte für Datenschutz und <em>Informationsfreiheit</em>",
            "Landesbeauftragte für Datenschutz und <em>Informationsfreiheit</em>\n\n\n    Inneres\n\n    Datenschutz\n\n    <em>Informationsfreiheit</em>",
        ],
        (
            "HmbTG Antrag auf Übersendung der beim Hamburgischen Beauftragten für Datenschutz und <em>Informationsfreiheit</em> [...] "
            # "Die Prüfung auf Übersendung der beim Hamburgischen Beauftragten für Datenschutz und <em>Informationsfreiheit</em> [...] "
            "Ihrer Mail vom 02.02.2017 auf Zugang zu der dem Hamburgischen Beauftragten für Datenschutz und <em>Informationsfreiheit</em> [...] "
            "Hintergrund war Ihr Antrag auf Zugang zu der dem Harnburgischen Beauftragten für Datenschutz und <em>Informationsfreiheit</em> [...] "
            "Monats nach Bekanntgabe Widerspruch bei dem Harnburgischen Beauftragten für Datenschutz und <em>Informationsfreiheit</em> [...] "
            "Möglichkeit, Widerspruch zu erheben - den Harnburgischen Beauftragten für Datenschutz und <em>Informationsfreiheit</em>"
            # "Der Hamburgische Beauftragte für Datenschutz und <em>Informationsfreiheit</em> [...] "
            # "Landesbeauftragte für Datenschutz und <em>Informationsfreiheit</em>"
        ),
    ),
    (
        [
            "<em>Schriftverkehr</em> zwischen BMI und AA in Bezug auf Schreiben an Seenotrettungsorganisationen\n\nSämtlichen",
            "<em>Schriftverkehr</em> zwischen dem BMI und dem AA in Bezug auf das Schreiben des MinDir Weinbrenneran Seenotrettungsorganisationen",
            "Information nicht vorhanden \n\n\n\n\n    \n    <em>Schriftverkehr</em> zwischen BMI und AA in Bezug auf Schreiben an",
            "&#x2F;VIG\r\n\r\nSehr geehrte&amp;lt;&amp;lt; Anrede &amp;gt;&amp;gt;\n\r\nbitte senden Sie mir Folgendes zu:\n\nSämtlichen <em>Schriftverkehr</em>",
            "notwendig wäre, besuchen Sie:\nhttps:&#x2F;&#x2F;fragdenstaat.de&#x2F;hilfe&#x2F;fuer-behoerden&#x2F;\n\n      \n    \n\n    \n    <em>Schriftverkehr</em>",
            "geehrter Herr Semsrott,\n\n\xa0\n\nin Erledigung Ihres IFG- Antrages teile ich Ihnen mit, dass kein\n<em>Schriftverkehr</em>",
        ],
        (
            "<em>Schriftverkehr</em> zwischen BMI und AA in Bezug auf Schreiben an Seenotrettungsorganisationen [...] "
            "<em>Schriftverkehr</em> zwischen dem BMI und dem AA in Bezug auf das Schreiben des MinDir Weinbrenneran Seenotrettungsorganisationen [...] "
            "<em>Schriftverkehr</em> zwischen BMI und AA in Bezug auf Schreiben an [...] "
            "Sämtlichen <em>Schriftverkehr</em> [...] "
            "in Erledigung Ihres IFG- Antrages teile ich Ihnen mit, dass kein\n<em>Schriftverkehr</em>"
        ),
    ),
]


@pytest.mark.parametrize(
    "highlight_list, query_highlight", test_cases, ids=[x[1][:20] for x in test_cases]
)
def test_es_queryset_wrapper_iter_highlight(highlight_list, query_highlight):
    obj = DummyObj(1)
    hit = DummyHit(1, {"field": highlight_list})
    qs = DummyQS([obj])
    es_response = [hit]

    wrapper = ESQuerySetWrapper(qs, es_response)
    result = list(wrapper)

    assert isinstance(result[0].query_highlight, SafeString)
    assert result[0].query_highlight == query_highlight


def test_es_queryset_wrapper_iter_no_highlight():
    obj = DummyObj(2)
    hit = DummyHit(2)
    qs = DummyQS([obj])
    es_response = [hit]

    wrapper = ESQuerySetWrapper(qs, es_response)
    result = list(wrapper)

    assert result[0].query_highlight == ""
