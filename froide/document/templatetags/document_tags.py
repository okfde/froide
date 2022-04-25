from django import template
from django.http import HttpRequest

from ..models import Document

register = template.Library()


@register.filter(name="can_write_document")
def can_write_document(document: Document, request: HttpRequest):
    return document.can_write(request)
