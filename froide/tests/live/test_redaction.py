import tempfile
from pathlib import Path
from typing import Literal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

import pytest
from filingcabinet.pdf_utils import page_to_png
from playwright.async_api import Playwright
from pypdf import PdfReader
from wand.image import Image

from froide.foirequest.models.attachment import FoiAttachment
from froide.foirequest.tests import factories
from froide.tests.live.utils import do_login

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.asyncio(loop_scope="session")
async def test_redaction(playwright: Playwright, world, live_server):
    browser = await playwright.chromium.launch(
        headless=False
    )  # this test only is reliable in headed mode
    page = await browser.new_page()

    factories.rebuild_index()
    user = User.objects.get(username="dummy")
    req = factories.FoiRequestFactory(
        user=user, created_at=timezone.now(), status="resolved"
    )
    mes = factories.FoiMessageFactory(request=req)

    att = factories.FoiAttachmentFactory(belongs_to=mes, approved=False)

    await do_login(page, live_server)

    path = reverse(
        "foirequest-redact_attachment",
        kwargs={"slug": req.slug, "attachment_id": att.id},
    )
    await page.goto(live_server.url + path)

    await page.locator("#pdf-viewer").scroll_into_view_if_needed()

    await page.wait_for_selector("canvas")
    await page.wait_for_timeout(100)

    # script to record mouse movement
    await page.evaluate("""
        const canvas = document.querySelector("canvas")

        let x, y
        window.coords = []

        document.addEventListener("mousemove", (e) => {
            x = e.clientX
            y = e.clientY
        })

        document.addEventListener("keydown", (e) => {
            if (e.key === "r") {
                const rect = canvas.getBoundingClientRect()
                window.coords.push([Math.round(x - rect.x), Math.round(y - rect.y)])
            }
        })
    """)

    instructions: list[Literal["zoom-in"] | list[tuple[int, int]]] = [
        [(375, 167), (411, 191)],
        "zoom-in",
        "zoom-in",
        [(680, 972), (879, 1002)],
    ]

    canvas = page.locator("canvas").first

    async def move(x: int, y: int):
        await page.locator(".redactContainer").hover()
        box = await canvas.bounding_box()
        assert box

        await page.mouse.move(box["x"] + x, box["y"] + y)
        await page.wait_for_timeout(100)

    for instruction in instructions:
        if instruction == "zoom-in":
            await page.get_by_test_id("zoom-in").click()
        elif isinstance(instruction, list):
            start, end = instruction

            await move(start[0], start[1])
            await page.mouse.down()
            await page.wait_for_timeout(100)
            await move(end[0], end[1])
            await page.mouse.up()
            await page.wait_for_timeout(100)

    await page.get_by_test_id("submit-redactions").click()

    url = reverse(
        "foirequest-manage_attachments",
        kwargs={"slug": req.slug, "message_id": mes.id},
    )

    await page.wait_for_url("**" + url)

    redacted = FoiAttachment.objects.get(belongs_to=mes, is_redacted=True)
    redacted_path = redacted.file.path
    target_path = Path(settings.MEDIA_ROOT) / "redaction-test-target.pdf"

    def to_png(filename, temp_dir):
        with PdfReader(filename) as pdf_reader:
            return page_to_png(
                pdf_reader=pdf_reader,
                filename=filename,
                temp_dir=temp_dir,
                page=1,
                max_dpi=300,
                max_resolution=2000,
                timeout=5,
            )[1]

    with (
        tempfile.TemporaryDirectory(delete=False) as temp_dir_target,
        tempfile.TemporaryDirectory(delete=False) as temp_dir_redacted,
    ):
        print(temp_dir_redacted)
        target_png = to_png(
            filename=target_path,
            temp_dir=Path(temp_dir_target),
        )

        redacted_png = to_png(
            filename=redacted_path,
            temp_dir=Path(temp_dir_redacted),
        )

        with (
            Image(filename=target_png) as target_img,
            Image(filename=redacted_png) as redacted_img,
        ):
            _, diff = target_img.compare(redacted_img, "root_mean_square")

            assert diff < 0.0001
