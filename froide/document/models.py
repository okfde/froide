from django.db import models

from filingcabinet.models import (
    AbstractDocument,
    AbstractDocumentCollection,
    CollectionDocument,
    Page,
    get_page_image_filename,
)
from filingcabinet.models import (
    DocumentCollectionManager as FCDocumentCollectionManager,
)
from filingcabinet.models import DocumentManager as FCDocumentManager

from froide.helper.auth import (
    can_read_object_authenticated,
    can_write_object,
    get_read_queryset,
    get_write_queryset,
)


class AuthQuerysetMixin:
    def get_authenticated_queryset(self, request):
        qs = self.get_queryset()
        return get_read_queryset(
            qs, request, has_team=True, public_field="public", scope="read:document"
        )


class DocumentManager(AuthQuerysetMixin, FCDocumentManager):
    pass


class Document(AbstractDocument):
    original = models.ForeignKey(
        "foirequest.FoiAttachment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="original_document",
    )

    foirequest = models.ForeignKey(
        "foirequest.FoiRequest", null=True, blank=True, on_delete=models.SET_NULL
    )
    publicbody = models.ForeignKey(
        "publicbody.PublicBody", null=True, blank=True, on_delete=models.SET_NULL
    )
    team = models.ForeignKey(
        "team.Team", null=True, blank=True, on_delete=models.SET_NULL
    )

    objects = DocumentManager()

    def is_public(self):
        return self.public

    def can_read(self, request):
        if self.can_read_unlisted(request):
            return True
        return can_read_object_authenticated(self, request=request)

    def can_write(self, request):
        return can_write_object(self, request=request)

    @classmethod
    def get_annotatable(cls, request):
        cond = models.Q(public=True, allow_annotation=True)
        return get_write_queryset(
            cls.objects.all(),
            request,
            has_team=True,
            user_write_filter=cond,
        )

    @classmethod
    def get_serializer_class(cls, detail=False):
        from .api_views import DocumentDetailSerializer, DocumentSerializer

        if detail:
            return DocumentDetailSerializer
        return DocumentSerializer

    def get_crossdomain_auth(self, filename=None):
        from .auth import DocumentCrossDomainMediaAuth

        if filename is None:
            filename = self.get_document_filename()

        return DocumentCrossDomainMediaAuth({"object": self, "filename": filename})

    def get_authorized_file_url(self, filename=None):
        if self.public:
            return self.get_file_url(filename=filename)
        return self.get_crossdomain_auth(filename=filename).get_full_media_url(
            authorized=True
        )

    def get_page_template(self, **kwargs):
        filename = get_page_image_filename(**kwargs)
        return self.get_authorized_file_url(filename=filename)

    def get_cover_image(self):
        return self.get_authorized_file_url(
            filename=get_page_image_filename(page=1, size="small")
        )

    @property
    def first_page(self):
        if not hasattr(self, "_first_page"):
            try:
                self._first_page = Page.objects.get(number=1, document=self)
            except Page.DoesNotExist:
                return None
        return self._first_page

    def get_cover_image_file(self):
        if self.first_page:
            return self.first_page.image
        return None


class DocumentCollectionManager(AuthQuerysetMixin, FCDocumentCollectionManager):
    pass


class DocumentCollection(AbstractDocumentCollection):
    team = models.ForeignKey(
        "team.Team", null=True, blank=True, on_delete=models.SET_NULL
    )
    foirequests = models.ManyToManyField("foirequest.FoiRequest", blank=True)

    objects = DocumentCollectionManager()

    def is_public(self):
        return self.public

    def can_read(self, request):
        if self.can_read_unlisted(request):
            return True
        return can_read_object_authenticated(self, request=request)

    def can_write(self, request):
        return can_write_object(self, request=request)

    @classmethod
    def get_serializer_class(cls):
        from .api_views import DocumentCollectionSerializer

        return DocumentCollectionSerializer

    def update_from_foirequests(self):
        existing_docs = CollectionDocument.objects.filter(collection=self).values_list(
            "document_id", flat=True
        )
        all_docs = Document.objects.filter(foirequest__in=self.foirequests.all())
        missing_docs = all_docs.exclude(id__in=existing_docs)
        for doc in missing_docs:
            CollectionDocument.objects.create(collection=self, document=doc)
