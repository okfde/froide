import json

from django import forms
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _

from froide.helper.templatetags.frontendbuild import get_frontend_build


def get_uppy_i18n():
    return {
        "addMore": _("Add more"),
        "addMoreFiles": _("Add more files"),
        "addingMoreFiles": _("Adding more files"),
        "allowAccessDescription": _(
            "In order to take pictures of your documents, please allow camera access."
        ),
        "allowAccessTitle": _("Please allow access to your camera"),
        # 'authenticateWith': _('Connect to %{pluginName}'),
        # 'authenticateWithTitle': _('Please authenticate with %{pluginName} to select files'),
        "back": _("Back"),
        "browse": _("browse"),
        "cancel": _("Cancel"),
        "cancelUpload": _("Cancel upload"),
        "chooseFiles": _("Choose files"),
        "closeModal": _("Close Modal"),
        # 'companionAuthError': _('Authorization required'),
        # 'companionError': _('Connection with Companion failed'),
        "complete": _("Complete"),
        "connectedToInternet": _("Connected to the Internet"),
        "copyLink": _("Copy link"),
        "copyLinkToClipboardFallback": _("Copy the URL below"),
        "copyLinkToClipboardSuccess": _("Link copied to clipboard"),
        "dashboardTitle": _("File Uploader"),
        "dashboardWindowTitle": _("File Uploader Window (Press escape to close)"),
        "dataUploadedOfTotal": _("%{complete} of %{total}"),
        "done": _("Done"),
        "dropHereOr": _("Drop files here or %{browse}"),
        "dropHint": _("Drop your files here"),
        "dropPaste": _("Drop files here, paste or %{browse}"),
        "dropPasteImport": _("Drop files here, paste, %{browse} or import from"),
        "edit": _("Edit"),
        "editFile": _("Edit file"),
        "editing": _("Editing %{file}"),
        "emptyFolderAdded": _("No files were added from empty folder"),
        "exceedsSize": _("This file exceeds maximum allowed size of"),
        "failedToUpload": _("Failed to upload %{file}"),
        "fileSource": _("File source: %{name}"),
        "filesUploadedOfTotal": {
            "0": _("%{complete} of %{smart_count} file uploaded"),
            "1": _("%{complete} of %{smart_count} files uploaded"),
            "2": _("%{complete} of %{smart_count} files uploaded"),
        },
        "filter": _("Filter"),
        "finishEditingFile": _("Finish editing file"),
        "folderAdded": {
            "0": _("Added %{smart_count} file from %{folder}"),
            "1": _("Added %{smart_count} files from %{folder}"),
            "2": _("Added %{smart_count} files from %{folder}"),
        },
        "import": _("Import"),
        "importFrom": _("Import from %{name}"),
        "link": _("Link"),
        "loading": _("Loading..."),
        "myDevice": _("My Device"),
        "noFilesFound": _("You have no files or folders here"),
        "noInternetConnection": _("No Internet connection"),
        "pause": _("Pause"),
        "pauseUpload": _("Pause upload"),
        "paused": _("Paused"),
        "preparingUpload": _("Preparing upload..."),
        "processingXFiles": {
            "0": _("Processing %{smart_count} file"),
            "1": _("Processing %{smart_count} files"),
            "2": _("Processing %{smart_count} files"),
        },
        "removeFile": _("Remove file"),
        "resetFilter": _("Reset filter"),
        "resume": _("Resume"),
        "resumeUpload": _("Resume upload"),
        "retry": _("Retry"),
        "retryUpload": _("Retry upload"),
        "saveChanges": _("Save changes"),
        "selectXFiles": {
            "0": _("Select %{smart_count} file"),
            "1": _("Select %{smart_count} files"),
            "2": _("Select %{smart_count} files"),
        },
        "takePicture": _("Take a picture"),
        "timedOut": _("Upload stalled for %{seconds} seconds, aborting."),
        "upload": _("Upload"),
        "uploadComplete": _("Upload complete"),
        "uploadFailed": _("Upload failed"),
        "uploadPaused": _("Upload paused"),
        "uploadXFiles": {
            "0": _("Upload %{smart_count} file"),
            "1": _("Upload %{smart_count} files"),
            "2": _("Upload %{smart_count} files"),
        },
        "uploadXNewFiles": {
            "0": _("Upload +%{smart_count} file"),
            "1": _("Upload +%{smart_count} files"),
            "2": _("Upload +%{smart_count} files"),
        },
        "uploading": _("Uploading"),
        "uploadingXFiles": {
            "0": _("Uploading %{smart_count} file"),
            "1": _("Uploading %{smart_count} files"),
            "2": _("Uploading %{smart_count} files"),
        },
        "xFilesSelected": {
            "0": _("%{smart_count} file selected"),
            "1": _("%{smart_count} files selected"),
            "2": _("%{smart_count} files selected"),
        },
        "xMoreFilesAdded": {
            "0": _("%{smart_count} more file added"),
            "1": _("%{smart_count} more files added"),
            "2": _("%{smart_count} more files added"),
        },
        "xTimeLeft": _("%{time} left"),
        "youCanOnlyUploadFileTypes": _("You can only upload: %{types}"),
    }


def get_widget_context():
    return {
        "settings": {
            "tusChunkSize": settings.DATA_UPLOAD_MAX_MEMORY_SIZE - (500 * 1024)
        },
        "i18n": {"uppy": get_uppy_i18n()},
        "url": {
            "tusEndpoint": reverse("api:upload-list"),
        },
    }


class FileUploader(forms.widgets.Input):
    input_type = "text"
    template_name = "upload/widgets/file_uploader.html"

    def __init__(self, allowed_file_types=None, *args, **kwargs):
        self.allowed_file_types = allowed_file_types
        super().__init__(*args, **kwargs)

    @property
    def media(self):
        build_info = get_frontend_build("fileuploader.js")
        return forms.Media(css={"all": build_info["css"]}, js=build_info["js"])

    def value_from_datadict(self, data, files, name):
        return data.getlist(name)

    def get_context(self, name, value=None, attrs=None):
        context = super().get_context(name, value, attrs)
        context["config"] = json.dumps(get_widget_context())
        context["allowed_file_types"] = json.dumps(self.allowed_file_types)
        return context


class FileUploaderField(forms.fields.CharField):
    def __init__(self, allowed_file_types=None, *args, **kwargs):
        super().__init__(
            widget=FileUploader(allowed_file_types=allowed_file_types),
            *args,
            **kwargs,
        )

    def clean(self, values):
        if len(values) == 0 and self.required:
            raise forms.ValidationError(self.error_messages["required"])
        return values
