from django.urls import path, re_path
from django.utils.translation import pgettext_lazy

from ..feeds import FoiRequestFeed, FoiRequestFeedAtom
from ..views import (
    shortlink, auth, show, suggest_public_body, set_public_body,
    set_status, send_message, escalation_message, make_public,
    confirm_request, delete_request,
    set_law, set_tags, set_summary, add_postal_reply,
    add_postal_message, add_postal_reply_attachment,
    set_message_sender, set_message_recipient, mark_not_foi,
    extend_deadline, approve_attachment, approve_message,
    make_same_request, resend_message,
    download_foirequest_zip, download_foirequest_pdf,
    show_attachment, redact_attachment,
    upload_attachments, delete_attachment, create_document,
    SetTeamView, edit_message, redact_message, download_message_pdf,
    publicbody_upload
)

urlpatterns = [
    re_path(r"^(?P<obj_id>\d+)$", shortlink, name="foirequest-notsolonglink"),
    path("<int:obj_id>/auth/<slug:code>/", auth, name="foirequest-longerauth"),
    path("<int:obj_id>/upload/<slug:code>/", publicbody_upload,
        name="foirequest-publicbody_upload"),
    path("<slug:slug>/", show, name="foirequest-show"),
    path("<slug:slug>/suggest/public-body/", suggest_public_body, name="foirequest-suggest_public_body"),
    path("<slug:slug>/set/public-body/", set_public_body, name="foirequest-set_public_body"),
    path("<slug:slug>/set/status/", set_status, name="foirequest-set_status"),
    path("<slug:slug>/send/message/", send_message, name="foirequest-send_message"),
    path("<slug:slug>/escalation/message/", escalation_message, name="foirequest-escalation_message"),
    path("<slug:slug>/make/public/", make_public, name="foirequest-make_public"),
    path("<slug:slug>/confirm-request/", confirm_request, name="foirequest-confirm_request"),
    path("<slug:slug>/delete-request/", delete_request, name="foirequest-delete_request"),
    path("<slug:slug>/set/law/", set_law, name="foirequest-set_law"),
    path("<slug:slug>/set/tags/", set_tags, name="foirequest-set_tags"),
    path("<slug:slug>/set/resolution/", set_summary, name="foirequest-set_summary"),
    path("<slug:slug>/add/postal-reply/", add_postal_reply, name="foirequest-add_postal_reply"),
    path("<slug:slug>/add/postal-message/", add_postal_message, name="foirequest-add_postal_message"),
    path("<slug:slug>/mark/not-foi/", mark_not_foi, name="foirequest-mark_not_foi"),
    path("<slug:slug>/extend-deadline/", extend_deadline, name="foirequest-extend_deadline"),
    path("<slug:slug>/make-same/", make_same_request, name="foirequest-make_same_request"),
    path("<slug:slug>/download/", download_foirequest_zip, name="foirequest-download"),
    path("<slug:slug>/pdf/", download_foirequest_pdf, name="foirequest-pdf"),
    path("<slug:slug>/set-team/", SetTeamView.as_view(), name="foirequest-set_team"),
    # Messages
    path("<slug:slug>/add/postal-reply/<int:message_id>/", add_postal_reply_attachment, name="foirequest-add_postal_reply_attachment"),
    path("<slug:slug>/approve/message/<int:message_id>/", approve_message, name="foirequest-approve_message"),
    path("<slug:slug>/<int:message_id>/set-sender-public-body/", set_message_sender, name="foirequest-set_message_sender"),
    path("<slug:slug>/<int:message_id>/set-recipient-public-body/", set_message_recipient, name="foirequest-set_message_recipient"),
    path("<slug:slug>/<int:message_id>/edit-message/", edit_message, name="foirequest-edit_message"),
    path("<slug:slug>/<int:message_id>/redact-message/", redact_message, name="foirequest-redact_message"),
    path("<slug:slug>/<int:message_id>/resend/", resend_message, name="foirequest-resend_message"),
    path("<slug:slug>/<int:message_id>/pdf/", download_message_pdf, name="foirequest-download_message_pdf"),
    # Attachments
    re_path(pgettext_lazy('url part', r'^(?P<slug>[-\w]+)/(?P<message_id>\d+)/attachment/(?P<attachment_name>.+)$'),
        show_attachment, name='foirequest-show_attachment'),
    # Attachment Upload
    re_path(pgettext_lazy('url part', r'^(?P<slug>[-\w]+)/(?P<message_id>\d+)/upload/$'),
        upload_attachments, name='foirequest-upload_attachments'),

    # Attachment actions
    path("<slug:slug>/redact/<int:attachment_id>/", redact_attachment, name="foirequest-redact_attachment"),
    path("<slug:slug>/approve/<int:attachment_id>/", approve_attachment, name="foirequest-approve_attachment"),
    path("<slug:slug>/delete/<int:attachment_id>/", delete_attachment, name="foirequest-delete_attachment"),
    path("<slug:slug>/create-doc/<int:attachment_id>/", create_document, name="foirequest-create_document"),

    # Feed
    path("<slug:slug>/feed/", FoiRequestFeedAtom(), name="foirequest-feed_atom"),
    path("<slug:slug>/rss/", FoiRequestFeed(), name="foirequest-feed")
]
