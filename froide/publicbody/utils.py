import json

from django.db.models import Q
from django.utils.text import slugify

from .models import PublicBody

import re
import html
from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension
from markdown.util import AtomicString


def export_user_data(user):
    pbs = PublicBody.objects.filter(
        Q(_created_by=user) |
        Q(_updated_by=user)
    )
    if not pbs:
        return
    yield ('publicbodies.json', json.dumps([
        {
            'created': pb._created_by_id == user.id,
            'updated': pb._updated_by_id == user.id,
            'created_timestamp': (
                pb.created_at.isoformat() if pb._created_by_id == user.id
                else None),
            'updated_timestamp': (
                pb.updated_at.isoformat() if pb._updated_by_id == user.id
                else None
            ),
            'url': pb.get_absolute_domain_short_url()
        }
        for pb in pbs]).encode('utf-8')
    )


# add anchors to law markdown
class LawTreeprocessor(Treeprocessor):
    def __init__(self, md):
        super().__init__(md)

        self.used_ids = set()
        self.header_rgx = re.compile('[Hh][123456]')

        # see https://regex101.com/r/pOR9CI/1
        self.paragraph_rgx = re.compile('(§)\s*(\d+)\s*([a-z]*)')

    def run(self, doc):
        for el in doc.iter():
            if isinstance(el.tag, str) and self.header_rgx.match(el.tag):
                text = self.get_title_text(el)

                if 'id' not in el.attrib:
                    # don't overwrite existing ids
                    el.attrib['id'] = self.get_title_id(text)

    def get_title_text(self, el):
        # get title text

        text = []
        for c in el.itertext():
            if isinstance(c, AtomicString):
                text.append(html.unescape(c))
            else:
                text.append(c)

        return ''.join(text).strip()

    def get_unique_id(self, id_name):
        if id_name not in self.used_ids:
            self.used_ids.add(id_name)
            # not used yet, so use it
            return id_name

        i = 1
        alternative_id = id_name

        # we need another one
        while alternative_id in self.used_ids:
            alternative_id = '{}-{}'.format(id_name, i)
            i += 1

        self.used_ids.add(alternative_id)
        return alternative_id

    def get_title_id(self, text):
        title_id = None

        if text.startswith("§"):
            result = self.paragraph_rgx.match(text)
            if result:
                title_id = ''.join(result.groups())

        if title_id is None:
            title_id = slugify(text)

        return self.get_unique_id(title_id)


class LawExtension(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(LawTreeprocessor(md), 'laws', 5)
