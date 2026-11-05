import json
from typing import Any
from unittest.mock import MagicMock, patch

import app
import names
import pytest
from bandcamp_api import BandcampError

HOST = "x.bandcamp.com"
BAND = "Band"
BAND_HIT = {"type": "b", "name": "Band", "item_url_root": f"https://{HOST}"}
RELEASES = [
    {"title": "First", "type": "album", "page_url": "/album/first"},
    {"title": "Second", "type": "album", "page_url": "/album/second"},
]
RELEASE: dict[str, Any] = {
    "current": {"title": "First"},
    "artist": "Artist",
    "trackinfo": [
        {"title": "Alpha", "track_num": 1, "duration": 60},
        {"title": "Beta", "track_num": 2, "duration": 90},
    ],
}


@pytest.fixture
def known() -> None:
    names.remember(
        {
            names.band_key(BAND): HOST,
            names.release_key(HOST, "First"): "album/first",
        }
    )


def titles(rows: list[dict[str, Any]]) -> list[str]:
    return [row["title"] for row in rows]


def test_empty_query_prompts() -> None:
    assert titles(app.run("")) == ["Type to search Bandcamp…"]


@patch("app.bandcamp_api.search", return_value=[])
def test_plain_text_searches(mock_search: MagicMock) -> None:
    assert titles(app.run("lofi")) == ["No results on Bandcamp"]
    mock_search.assert_called_once_with("lofi")


@patch("browse.bandcamp_api.get_release", new=MagicMock(return_value={}))
@patch("browse.images.warm", new=MagicMock(return_value={}))
@patch("app.bandcamp_api.search", new=MagicMock(return_value=[BAND_HIT]))
@patch("app.bandcamp_api.get_band_releases", return_value=RELEASES)
def test_band_page_lists_releases_under_a_header(mock_get: MagicMock) -> None:
    rows = app.run(f"{BAND} > ")
    mock_get.assert_called_once_with(f"https://{HOST}")
    assert titles(rows) == [BAND, "First", "Second"]
    assert rows[0]["arg"] == f"https://{HOST}"
    assert rows[0]["autocomplete"] == ""
    assert rows[1]["autocomplete"] == f"{BAND} > First > "


@patch("browse.bandcamp_api.get_release", new=MagicMock(return_value={}))
@patch("browse.images.warm", new=MagicMock(return_value={}))
@patch("app.bandcamp_api.search", new=MagicMock(return_value=[]))
def test_unknown_band_is_an_error() -> None:
    with pytest.raises(BandcampError):
        app.run("Nobody > ")


@pytest.mark.usefixtures("known")
@patch("tracklist.images.warm", new=MagicMock(return_value={}))
@patch("app.bandcamp_api.get_band_releases", new=MagicMock(return_value=RELEASES))
@patch("app.bandcamp_api.get_release", return_value=RELEASE)
def test_release_resolved_from_the_band_page_when_not_remembered(
    mock_get: MagicMock,
) -> None:
    app.run(f"{BAND} > second > ")
    mock_get.assert_called_once_with(f"https://{HOST}/album/second")
    with pytest.raises(BandcampError):
        app.run(f"{BAND} > Missing > ")


@patch("browse.bandcamp_api.get_release", new=MagicMock(return_value={}))
@patch("browse.images.warm", new=MagicMock(return_value={}))
@patch("app.bandcamp_api.get_band_releases", new=MagicMock(return_value=RELEASES))
@pytest.mark.usefixtures("known")
def test_band_page_filters_releases() -> None:
    assert titles(app.run(f"{BAND} > sec")) == [BAND, "Second"]
    assert titles(app.run(f"{BAND} > zzz")) == [BAND, "No release matches 'zzz'"]


@patch("tracklist.images.warm", new=MagicMock(return_value={}))
@patch("app.bandcamp_api.get_release", return_value=RELEASE)
@pytest.mark.usefixtures("known")
def test_release_page_lists_tracks_under_a_header(mock_get: MagicMock) -> None:
    rows = app.run(f"{BAND} > First > ")
    mock_get.assert_called_once_with(f"https://{HOST}/album/first")
    assert titles(rows) == ["First", "1. Alpha", "2. Beta"]
    assert rows[0]["arg"] == f"https://{HOST}/album/first"
    assert rows[0]["autocomplete"] == f"{BAND} > "
    assert rows[1]["arg"] == f"https://{HOST}/album/first"


@patch("tracklist.images.warm", new=MagicMock(return_value={}))
@patch("app.bandcamp_api.get_release", new=MagicMock(return_value=RELEASE))
@pytest.mark.usefixtures("known")
def test_release_page_filters_tracks() -> None:
    assert titles(app.run(f"{BAND} > First > bet")) == ["First", "2. Beta"]
    assert titles(app.run(f"{BAND} > First > zzz"))[1] == "No track matches 'zzz'"


@patch("tracklist.images.warm", new=MagicMock(return_value={}))
@patch("app.bandcamp_api.get_release", new=MagicMock(return_value={"trackinfo": []}))
@pytest.mark.usefixtures("known")
def test_release_without_a_title_uses_its_path() -> None:
    assert app.run(f"{BAND} > First > ")[0]["title"] == "First"


@patch("app.bandcamp_api.search", new=MagicMock(side_effect=BandcampError("boom")))
def test_main_surfaces_bandcamp_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    stored: dict[str, Any] = {}

    def store(_directory: object, query: str, payload: dict[str, Any]) -> None:
        stored[query] = payload

    monkeypatch.setattr("app.finish", store)
    app.main(["--job", "query"])
    assert "boom" in stored["query"]["items"][0]["title"]


def test_main_without_arguments_prompts(capsys: pytest.CaptureFixture[str]) -> None:
    app.main([])
    assert "Type to search" in capsys.readouterr().out


def served(*_args: object, **_kwargs: object) -> dict[str, Any]:
    return {"items": [{"title": "x"}]}


def test_main_serves_the_view_for_a_query(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("app.serve", served)
    app.main(["lofi"])
    assert json.loads(capsys.readouterr().out)["items"][0]["title"] == "x"


def test_job_stores_the_view(monkeypatch: pytest.MonkeyPatch) -> None:
    stored: dict[str, Any] = {}

    def store(_directory: object, query: str, payload: dict[str, Any]) -> None:
        stored[query] = payload

    monkeypatch.setattr("app.finish", store)
    app.main(["--job", ""])
    assert stored[""]["items"][0]["title"] == "Type to search Bandcamp…"


def test_job_stores_an_error_row_when_the_view_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored: dict[str, Any] = {}

    def store(_directory: object, query: str, payload: dict[str, Any]) -> None:
        stored[query] = payload

    def fail(*_args: object) -> list[dict[str, Any]]:
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr("app.finish", store)
    monkeypatch.setattr("app.run", fail)
    app.main(["--job", "q"])
    assert stored["q"]["items"][0]["title"] == "boom"


def test_loading_labels_name_what_is_loading() -> None:
    assert app.loading_label("lofi") == "Searching Bandcamp for 'lofi'…"
    assert app.loading_label("Band > ") == "Loading Band releases…"
    assert app.loading_label("Band > First > ") == "Loading First tracks…"
