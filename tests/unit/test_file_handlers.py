"""Regression tests for forwarded captions and manual season input."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import handlers.files as files_module
from core.ai_parser import AIParseResult
from core.tmdb_client import TMDBClient
from handlers.files import FileHandlers
from models.download import DownloadInfo, MediaType, SeriesInfo, TMDBResult

CAPTION = "Jeepers Creepers 3 [SUB-ITA] (2017)\n\n16/02/2024, 14:45:59 da walker111"


@pytest.fixture
def handler():
    instance = FileHandlers.__new__(FileHandlers)
    instance.logger = Mock()
    instance.auth = SimpleNamespace(check_authorized=AsyncMock(return_value=True))
    instance.config = SimpleNamespace(
        paths=SimpleNamespace(movies=Path("/movies"), tv=Path("/tv")),
        limits=SimpleNamespace(max_file_size_gb=10, min_free_space_gb=1),
    )
    instance.downloads = SimpleNamespace(
        active_downloads={},
        add_download=Mock(return_value=True),
        queue_download=AsyncMock(return_value=1),
        get_active_downloads=Mock(return_value=[]),
    )
    instance.space = SimpleNamespace(check_space_available=Mock(return_value=(True, 100)))
    instance.database = None
    return instance


def file_event(caption, filename=None):
    return SimpleNamespace(
        file=SimpleNamespace(name=filename, size=800 * 1024**2),
        document=SimpleNamespace(attributes=[]),
        message=SimpleNamespace(id=347, message=caption),
        sender_id=123,
        text=caption,
        reply=AsyncMock(return_value=SimpleNamespace(edit=AsyncMock())),
    )


@pytest.mark.parametrize("filename", [None, "opaque_name.mkv"])
def test_forwarded_caption_preserves_title_and_year(handler, filename):
    detected, original = handler._extract_filename(file_event(CAPTION, filename))

    extension = ".mkv" if filename else ".mp4"
    assert detected == f"Jeepers Creepers 3 [SUB-ITA] (2017){extension}"
    if filename:
        assert original == filename
    else:
        assert original.startswith("video_")
    assert "walker111" not in detected


@pytest.mark.parametrize(
    "metadata",
    [
        "16/02/2024, 14:45:59 da walker111",
        "> ***16/02/2024, 14:45:59 da walker111***",
        "16022024\n14:45:59\nda walker111",
    ],
)
def test_metadata_only_caption_uses_real_filename(handler, metadata):
    detected, original = handler._extract_filename(file_event(metadata, "Film.2017.mkv"))

    assert detected == original == "Film.2017.mkv"


@pytest.mark.parametrize(
    "title",
    [
        "Il ragazzo da un milione di dollari (2014)",
        "Scary Movie (2000)",
        "1917 (2019)",
        "The Walking Dead S02E03",
    ],
)
def test_titles_are_not_discarded_as_forwarding_metadata(handler, title):
    detected, _ = handler._extract_filename(file_event(f"{title}\n\n16/02/2024, 14:45:59 da walker111"))

    assert detected == f"{title}.mp4"


@pytest.mark.parametrize("ai_available", [True, False])
async def test_nameless_forwarded_movie_is_queued_as_correct_movie(handler, monkeypatch, ai_available):
    movie = TMDBResult(
        id=55341,
        title="Jeepers Creepers 3",
        original_title="Jeepers Creepers 3",
        media_type="movie",
        year="2017",
        overview="",
    )
    handler.ai_parser = SimpleNamespace(
        is_available=ai_available,
        parse=AsyncMock(return_value=AIParseResult(title=movie.title, media_type="movie", year="2017")),
    )
    handler.tmdb = TMDBClient.__new__(TMDBClient)
    handler.tmdb.search = AsyncMock(return_value=[movie])
    monkeypatch.setattr(files_module, "get_user_config_for_download", AsyncMock(return_value=None))
    event = file_event(CAPTION)

    await handler.file_handler(event)

    download = handler.downloads.queue_download.await_args.args[0]
    assert download.selected_tmdb.id == 55341
    assert download.is_movie is True
    assert download.media_type == MediaType.MOVIE
    assert download.dest_path == Path("/movies")
    assert download.waiting_for_season is False
    if ai_available:
        handler.ai_parser.parse.assert_awaited_once_with("Jeepers Creepers 3 [SUB-ITA] (2017).mp4")
    else:
        handler.ai_parser.parse.assert_not_awaited()


async def test_forwarded_file_does_not_answer_pending_season_prompt(handler):
    waiting = DownloadInfo(
        message_id=345,
        user_id=123,
        filename="Show.mp4",
        original_filename="Show.mp4",
        size=1024,
        waiting_for_season=True,
    )
    handler.downloads.active_downloads[345] = waiting
    event = file_event(CAPTION)

    await handler.text_handler(event)

    event.reply.assert_not_awaited()
    handler.downloads.queue_download.assert_not_awaited()
    assert waiting.waiting_for_season is True


async def test_plain_text_season_reply_still_queues_tv_download(handler):
    waiting = DownloadInfo(
        message_id=345,
        user_id=123,
        filename="Show.mp4",
        original_filename="Show.mp4",
        size=1024,
        series_info=SeriesInfo(series_name="Show"),
        dest_path=Path("/tv"),
        waiting_for_season=True,
    )
    handler.downloads.active_downloads[345] = waiting
    event = SimpleNamespace(file=None, text="2", sender_id=123, reply=AsyncMock())

    await handler.text_handler(event)

    assert waiting.waiting_for_season is False
    assert waiting.selected_season == 2
    handler.downloads.queue_download.assert_awaited_once_with(waiting)


def test_text_handler_registration_excludes_file_captions(handler):
    registrations = []
    handler.client = SimpleNamespace(on=lambda builder: lambda callback: registrations.append((builder, callback)))

    handler.register()

    text_filter = registrations[1][0].func
    assert not text_filter(file_event(CAPTION))
    assert text_filter(SimpleNamespace(file=None, text="2"))
    assert not text_filter(SimpleNamespace(file=None, text="/status"))
