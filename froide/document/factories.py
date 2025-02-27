import factory
from factory.django import DjangoModelFactory

from froide.foirequest.tests.factories import FoiAttachmentFactory, FoiRequestFactory
from froide.publicbody.factories import PublicBodyFactory

from .models import Document


class DocumentFactory(DjangoModelFactory):
    class Meta:
        model = Document

    title = factory.Sequence(lambda n: "Document {0}".format(n))
    original = factory.SubFactory(FoiAttachmentFactory)
    foirequest = factory.SubFactory(FoiRequestFactory)
    publicbody = factory.SubFactory(PublicBodyFactory)
