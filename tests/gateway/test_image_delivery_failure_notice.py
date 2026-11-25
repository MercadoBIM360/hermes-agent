"""An image the platform refused must not vanish silently: the reply text already lost its MEDIA tag,
so the base dispatch sends the same failure notice the non-image attachments get."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from gateway.config import PlatformConfig
from gateway.platforms.base import SendResult
from gateway.platforms.event import MessageEvent
from gateway.session import Platform, SessionSource
from plugins.platforms.mattermost.adapter import MattermostAdapter


def _adapter(send_result: SendResult) -> MattermostAdapter:
    adapter = MattermostAdapter(PlatformConfig(enabled=True, token="mm-token", extra={"url": "https://mm.example"}))
    adapter.send_multiple_images = AsyncMock(return_value=send_result)
    adapter._notify_media_delivery_failure = AsyncMock()
    return adapter


async def _deliver(adapter: MattermostAdapter, image) -> list:
    event = MessageEvent(text="", source=SessionSource(platform=Platform.MATTERMOST, chat_id="chan-1"))
    results = []
    await adapter._deliver_media_attachments(
        event, [(str(image), False)], [], force_document_attachments=False, human_delay=0,
        metadata={}, record_delivery=results.append)
    return results


@pytest.mark.asyncio
async def test_failed_image_sends_a_failure_notice(tmp_path) -> None:
    image = tmp_path / "render iso.png"
    image.write_bytes(b"\x89PNG")
    adapter = _adapter(SendResult(success=False, error="all images failed to send"))

    results = await _deliver(adapter, image)

    assert [r.success for r in results] == [False]
    adapter._notify_media_delivery_failure.assert_awaited_once()
    assert adapter._notify_media_delivery_failure.await_args.args == ("chan-1", str(image))


@pytest.mark.asyncio
async def test_delivered_image_sends_no_notice(tmp_path) -> None:
    image = tmp_path / "render.png"
    image.write_bytes(b"\x89PNG")
    adapter = _adapter(SendResult(success=True, message_id="post-1"))

    await _deliver(adapter, image)

    adapter._notify_media_delivery_failure.assert_not_awaited()
