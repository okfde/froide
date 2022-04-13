from django.test import TestCase

from froide.foirequest.models import FoiAttachment
from froide.helper.storage import get_numbered_filename


class HelperTest(TestCase):
    def test_shouldReturnTheFilename_whenTheFilenameDoesNotExistYet(self):
        filename = "test123.pdf"
        attachment = FoiAttachment()
        attachment.name = "something_else.pdf"

        actual_new_filename = get_numbered_filename([attachment], filename)

        self.assertEqual(actual_new_filename, "test123.pdf")

    def test_shouldReturnAFilenameNumberedWithOne_whenTheFilenameAlreadyExist(self):
        filename = "test123.pdf"
        attachment = FoiAttachment()
        attachment.name = "test123.pdf"

        actual_new_filename = get_numbered_filename([attachment], filename)

        self.assertEqual(actual_new_filename, "test123_1.pdf")

    def test_shouldReturnAFilenameNumberedWithTwo_whenTheFilenameAndTheFilenameNumberedWithOneAlreadyExist(
            self,
    ):
        filename = "test123.pdf"
        attachment1 = FoiAttachment()
        attachment1.name = "test123.pdf"
        attachment2 = FoiAttachment()
        attachment2.name = "test123_1.pdf"

        actual_new_filename = get_numbered_filename(
            [attachment1, attachment2], filename
        )

        self.assertEqual(actual_new_filename, "test123_2.pdf")
