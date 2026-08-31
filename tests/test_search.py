from unittest.mock import patch

from bandcamp_api import BandcampError
from search import LIVE_TYPING_TIMEOUT_SECONDS, build_items, main

DEFAULT_TIMEOUT_SECONDS = 5


@patch("search.images.warm", return_value={})
def test_build_items_empty_list_shows_no_results(_mock_warm):
    items = build_items([])
    assert len(items) == 1
    assert items[0]["valid"] is False


@patch("search.images.warm", return_value={"https://img/a.jpg": "/tmp/a.jpg"})
def test_build_items_band_row(_mock_warm):
    entries = [
        {
            "type": "b",
            "is_label": False,
            "name": "Aphex Twin",
            "item_url_root": "https://aphextwin.bandcamp.com",
            "img": "https://img/a.jpg",
        }
    ]
    result = build_items(entries)[0]
    assert result["title"] == "Aphex Twin"
    assert result["subtitle"] == "Band"
    assert result["arg"] == "https://aphextwin.bandcamp.com"
    assert result["icon"] == {"path": "/tmp/a.jpg"}
    assert result["variables"] == {
        "BC_TYPE": "band",
        "BC_URL": "https://aphextwin.bandcamp.com",
    }


@patch("search.images.warm", return_value={})
def test_build_items_label_row_shows_label_subtitle(_mock_warm):
    entries = [
        {
            "type": "b",
            "is_label": True,
            "name": "Warp Records",
            "item_url_root": "https://warprecords.bandcamp.com",
        }
    ]
    result = build_items(entries)[0]
    assert result["subtitle"] == "Label"
    assert result["icon"] == {"path": "icons/icon_label.png"}


@patch("search.images.warm", return_value={})
def test_build_items_album_row_prefixes_band_name(_mock_warm):
    entries = [
        {
            "type": "a",
            "name": "Drukqs",
            "band_name": "Aphex Twin",
            "item_url_root": "https://aphextwin.bandcamp.com",
            "item_url_path": "https://aphextwin.bandcamp.com/album/drukqs",
        }
    ]
    result = build_items(entries)[0]
    assert result["title"] == "Aphex Twin - Drukqs"
    assert result["subtitle"] == "Album"
    assert result["arg"] == "https://aphextwin.bandcamp.com/album/drukqs"
    assert result["variables"] == {
        "BC_TYPE": "release",
        "BC_URL": "https://aphextwin.bandcamp.com/album/drukqs",
    }


@patch("search.images.warm", return_value={})
def test_build_items_album_row_includes_tags(_mock_warm):
    entries = [
        {
            "type": "a",
            "name": "Drukqs",
            "item_url_root": "https://aphextwin.bandcamp.com",
            "item_url_path": "https://aphextwin.bandcamp.com/album/drukqs",
            "tag_names": ["Electronic", "United Kingdom"],
        }
    ]
    result = build_items(entries)[0]
    assert result["subtitle"] == "Album・Electronic, United Kingdom"


@patch("search.images.warm", return_value={})
def test_build_items_album_row_caps_tags_at_three(_mock_warm):
    entries = [
        {
            "type": "a",
            "name": "Drukqs",
            "item_url_root": "https://aphextwin.bandcamp.com",
            "item_url_path": "https://aphextwin.bandcamp.com/album/drukqs",
            "tag_names": ["Electronic", "IDM", "Experimental", "UK", "Braindance"],
        }
    ]
    result = build_items(entries)[0]
    assert result["subtitle"] == "Album・Electronic, IDM, Experimental"


@patch("search.images.warm", return_value={})
def test_build_items_album_row_without_tags_shows_plain_type(_mock_warm):
    entries = [
        {
            "type": "a",
            "name": "Drukqs",
            "item_url_root": "https://aphextwin.bandcamp.com",
            "item_url_path": "https://aphextwin.bandcamp.com/album/drukqs",
        }
    ]
    result = build_items(entries)[0]
    assert result["subtitle"] == "Album"


@patch("search.images.warm", return_value={})
def test_build_items_track_row(_mock_warm):
    entries = [
        {
            "type": "t",
            "name": "Windowlicker",
            "band_name": "Aphex Twin",
            "item_url_root": "https://aphextwin.bandcamp.com",
            "item_url_path": "https://aphextwin.bandcamp.com/track/windowlicker",
        }
    ]
    result = build_items(entries)[0]
    assert result["subtitle"] == "Track"
    assert result["icon"] == {"path": "icons/icon_track.png"}


@patch("search.images.warm", return_value={})
def test_build_items_uses_short_timeout_for_live_typing(mock_warm):
    entries = [
        {"type": "b", "name": "A Band", "item_url_root": "https://a.bandcamp.com"}
    ]
    build_items(entries)
    assert (
        mock_warm.call_args.kwargs["timeout_seconds"]
        == LIVE_TYPING_TIMEOUT_SECONDS
        < DEFAULT_TIMEOUT_SECONDS
    )


def test_main_prompts_on_empty_query(capsys):
    main([""])
    out = capsys.readouterr().out
    assert "Type to search" in out


@patch("search.images.warm", return_value={})
@patch("search.bandcamp_api.search", side_effect=BandcampError("boom"))
def test_main_surfaces_bandcamp_error(_mock_search, _mock_warm, capsys):
    main(["query"])
    out = capsys.readouterr().out
    assert "boom" in out
