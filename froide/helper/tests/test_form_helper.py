from django import forms

import pytest
from lxml.html import HtmlElement, fragment_fromstring

from ..templatetags.form_helper import render_field

CHOICES = [("a", "A"), ("b", "B")]

# The templates `render_field` picks between, as its keyword arguments.
VARIANTS = {
    "horizontal": {},
    "stacked": {"stacked": True},
    "inline": {"inline": True},
}


class DescribedForm(forms.Form):
    """One field per branch of the field templates, each with a help text."""

    text = forms.CharField(help_text="Help for text")
    textarea = forms.CharField(widget=forms.Textarea, help_text="Help for textarea")
    select = forms.ChoiceField(choices=CHOICES, help_text="Help for select")
    checkbox = forms.BooleanField(help_text="Help for checkbox")
    radio = forms.ChoiceField(
        widget=forms.RadioSelect, choices=CHOICES, help_text="Help for radio"
    )
    multi = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=CHOICES,
        help_text="Help for multi",
    )


FIELD_NAMES = list(DescribedForm().fields)


def render(
    form: DescribedForm, field_name: str, variant: str
) -> tuple[forms.BoundField, HtmlElement]:
    """Render a field using our custom Bootstrap form field templates."""

    field = form[field_name]
    html = render_field(field, **VARIANTS[variant])
    return field, fragment_fromstring(html, create_parent="div")


def present_ids(tree: HtmlElement) -> set[str]:
    """Every id defined in the field's markup - every possible reference target."""

    return set(tree.xpath("//@id"))


def referenced_ids(tree: HtmlElement) -> set[str]:
    """Every id referenced by an `aria-describedby` in the field's markup."""

    ids = set()
    for element in tree.iter():
        # `aria-describedby` holds a whitespace-separated list of ids.
        ids.update(element.get("aria-describedby", "").split())
    return ids


def hidden_errors(tree: HtmlElement) -> list[HtmlElement]:
    """The error blocks that Bootstrap will not display.

    `.invalid-feedback` is `display: none` until a preceding sibling carries
    `.is-invalid`, so a control nested in a `.form-check` never reveals the block
    below the group. A block with `d-block` is displayed wherever it sits.
    """

    return [
        block
        for block in tree.xpath('//*[contains(@class, "invalid-feedback")]')
        if "d-block" not in (block.get("class") or "")
        and not any(
            "is-invalid" in (sibling.get("class") or "")
            for sibling in block.itersiblings(preceding=True)
        )
    ]


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("field_name", FIELD_NAMES)
def test_help_text_is_linked(field_name: str, variant: str):
    field, tree = render(DescribedForm(), field_name, variant)
    help_id = f"{field.auto_id}_helptext"

    assert help_id in present_ids(tree), (
        f"{field_name}: help text is rendered without the expected id "
        f"({help_id}), so it cannot be referenced"
    )
    assert help_id in referenced_ids(tree), (
        f"{field_name}: nothing references the help text ({help_id}), so a "
        "screen reader does not announce it"
    )


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("field_name", FIELD_NAMES)
def test_error_is_linked(field_name: str, variant: str):
    # Every field is required, so an empty submission puts an error on each.
    form = DescribedForm(data={})
    assert form[field_name].errors

    field, tree = render(form, field_name, variant)
    error_id = f"{field.auto_id}_error"

    assert error_id in present_ids(tree), (
        f"{field_name}: the error message is rendered without the expected "
        f"id ({error_id}), so it cannot be referenced"
    )
    assert error_id in referenced_ids(tree), (
        f"{field_name}: nothing references the error message ({error_id}), so "
        "a screen reader does not announce it"
    )


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("field_name", FIELD_NAMES)
def test_error_is_displayed(field_name: str, variant: str):
    form = DescribedForm(data={})
    assert form[field_name].errors

    _, tree = render(form, field_name, variant)

    assert not hidden_errors(tree), (
        f"{field_name}: the error message is in the markup but never displayed"
    )


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("field_name", FIELD_NAMES)
def test_no_dangling_references(field_name: str, variant: str):
    # Bound and invalid, so help text and error are both referenced.
    field, tree = render(DescribedForm(data={}), field_name, variant)

    dangling = referenced_ids(tree) - present_ids(tree)
    assert not dangling, (
        f"{field_name}: aria-describedby points to ids that do not exist in "
        f"the markup: {', '.join(sorted(dangling))}"
    )
