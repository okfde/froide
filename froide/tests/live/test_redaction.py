from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

import pytest
from factory.django import FileField
from playwright.async_api import Page
from wand.image import Image

from froide.foirequest.models.attachment import FoiAttachment
from froide.foirequest.tests import factories
from froide.tests.live.utils import do_login

User = get_user_model()


def smooth_color(color: int):
    # smooth out color due to dithering (the small rects get tiny)
    if color < 6:
        return 0
    if color > 249:
        return 255
    return color


def get_colors_from_image(image: Image) -> set:
    colors = set()
    blob = image.export_pixels(channel_map="RGB")
    assert blob

    for cursor in range(0, image.width * image.height * 3, 3):
        pixel = [blob[cursor], blob[cursor + 1], blob[cursor + 2]]
        pixel = [smooth_color(c) for c in pixel]
        colors.add(tuple(pixel))

    return colors


@pytest.mark.django_db
@pytest.mark.asyncio(loop_scope="session")
@override_settings(SERVE_MEDIA=True)
async def test_redaction(world, live_server, settings, page: Page):
    media_root = Path(settings.MEDIA_ROOT)
    test_path = media_root / "redaction-test-precision.pdf"
    target_path = media_root / "redaction-test-precision-target.pdf"

    user = User.objects.get(username="dummy")
    req = factories.FoiRequestFactory(
        user=user, created_at=timezone.now(), status="resolved"
    )
    mes = factories.FoiMessageFactory(request=req)

    att = factories.FoiAttachmentFactory(
        belongs_to=mes, approved=False, file=FileField(from_path=test_path)
    )

    await do_login(page, live_server)

    path = reverse(
        "foirequest-redact_attachment",
        kwargs={"slug": req.slug, "attachment_id": att.id},
    )
    await page.goto(live_server.url + path)

    await page.locator("#pdf-viewer").scroll_into_view_if_needed()

    await page.wait_for_selector("canvas")

    # x, y, width, height in cm (absolute on a4)
    instructions = [
        "zoom-in",
        [12, 4, 6, 2],
    ]

    a4_width = 21
    a4_height = 29.7

    canvas = page.locator("canvas").first

    async def redact(x: float, y: float, width: float, height: float):
        canvas_pos = await canvas.bounding_box()
        assert canvas_pos
        await page.mouse.move(canvas_pos["x"], canvas_pos["y"])

        # make sure canvas is a4 (or very close to a4)
        a4_ratio = a4_width / a4_height
        canvas_ratio = canvas_pos["width"] / canvas_pos["height"]
        assert abs(canvas_ratio - a4_ratio) < 0.01

        # rescale absolute a4 sizes relative to canvas
        scalar_x = a4_width / canvas_pos["width"]
        scalar_y = a4_height / canvas_pos["height"]

        start_x = canvas_pos["x"] + x / scalar_x
        start_y = canvas_pos["y"] + y / scalar_y
        end_x = start_x + width / scalar_x
        end_y = start_y + height / scalar_y

        await page.mouse.move(round(start_x), round(start_y))
        await page.mouse.down()
        await page.mouse.move(round(end_x), round(end_y))
        await page.mouse.up()

    for instruction in instructions:
        if instruction == "zoom-in":
            await page.get_by_test_id("zoom-in").click()

            # FIXME: don't rely on timeout, but waiting for stable element doesn't do it
            await page.wait_for_timeout(500)
        elif isinstance(instruction, list):
            await redact(*instruction)

    await page.get_by_test_id("submit-redactions").click()

    url = reverse(
        "foirequest-manage_attachments",
        kwargs={"slug": req.slug, "message_id": mes.id},
    )

    await page.wait_for_url("**" + url)

    redacted = FoiAttachment.objects.get(belongs_to=mes, is_redacted=True)
    assert redacted
    redacted_path = redacted.file.path
    assert redacted_path

    with (
        Image(filename=target_path, resolution=300) as target_img,
        Image(filename=redacted_path, resolution=300) as redacted_img,
    ):
        diff = target_img.get_image_distortion(redacted_img, "root_mean_square")

        # for debugging:
        # target_img.save(filename="target.png")
        # redacted_img.save(filename="redacted.png")

        assert diff < 0.025

        colors = get_colors_from_image(redacted_img)

        # make sure there is no red left
        assert (255, 0, 0) not in colors

        # make sure elements near redaction are still present
        assert (0, 255, 0) in colors  # green
        assert (255, 0, 255) in colors  # magenta
        assert (0, 255, 255) in colors  # cyan
        assert (255, 255, 0) in colors  # yellow
