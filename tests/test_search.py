from unittest.mock import MagicMock, patch

from search import LIVE_TYPING_TIMEOUT_SECONDS, build_items

DEFAULT_TIMEOUT_SECONDS = 5


@patch("search.images.warm", return_value={})
def test_build_items_empty_list_shows_no_results(mock_warm: MagicMock) -> None:
    items = build_items([])
    mock_warm.assert_not_called()
    assert len(items) == 1
    assert items[0]["valid"] is False


@patch(
    "search.images.warm",
    new=MagicMock(return_value={"https://img/a.jpg": "/cache/a.jpg"}),
)
def test_build_items_band_row() -> None:
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
    assert result["subtitle"] == "Band · ⌥↩ Open in browser"
    assert result["valid"] is False
    assert result["autocomplete"] == "Aphex Twin > "
    assert result["mods"]["alt"]["arg"] == "https://aphextwin.bandcamp.com"
    assert result["icon"] == {"path": "/cache/a.jpg"}


@patch("search.images.warm", new=MagicMock(return_value={}))
def test_build_items_label_row_shows_label_subtitle() -> None:
    entries = [
        {
            "type": "b",
            "is_label": True,
            "name": "Warp Records",
            "item_url_root": "https://warprecords.bandcamp.com",
        }
    ]
    result = build_items(entries)[0]
    assert result["subtitle"] == "Label · ⌥↩ Open in browser"
    assert result["icon"] == {"path": "icons/icon_label.png"}


@patch("search.images.warm", new=MagicMock(return_value={}))
def test_build_items_album_row_prefixes_band_name() -> None:
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
    assert result["subtitle"] == "Album · ⌥↩ Open in browser"
    assert result["autocomplete"] == "Aphex Twin > Drukqs > "
    assert result["mods"]["alt"]["arg"] == "https://aphextwin.bandcamp.com/album/drukqs"


@patch("search.images.warm", new=MagicMock(return_value={}))
def test_build_items_album_row_includes_tags() -> None:
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
    assert (
        result["subtitle"] == "Album・Electronic, United Kingdom · ⌥↩ Open in browser"
    )


@patch("search.images.warm", new=MagicMock(return_value={}))
def test_build_items_album_row_caps_tags_at_three() -> None:
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
    assert (
        result["subtitle"]
        == "Album・Electronic, IDM, Experimental · ⌥↩ Open in browser"
    )


@patch("search.images.warm", new=MagicMock(return_value={}))
def test_build_items_album_row_without_tags_shows_plain_type() -> None:
    entries = [
        {
            "type": "a",
            "name": "Drukqs",
            "item_url_root": "https://aphextwin.bandcamp.com",
            "item_url_path": "https://aphextwin.bandcamp.com/album/drukqs",
        }
    ]
    result = build_items(entries)[0]
    assert result["subtitle"] == "Album · ⌥↩ Open in browser"


@patch("search.images.warm", new=MagicMock(return_value={}))
def test_build_items_track_row() -> None:
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
    assert result["subtitle"] == "Track · ⌥↩ Open in browser"
    assert result["icon"] == {"path": "icons/icon_track.png"}


@patch("search.images.warm", return_value={})
def test_build_items_uses_short_timeout_for_live_typing(mock_warm: MagicMock) -> None:
    entries = [
        {"type": "b", "name": "A Band", "item_url_root": "https://a.bandcamp.com"}
    ]
    build_items(entries)
    assert (
        mock_warm.call_args.kwargs["timeout_seconds"]
        == LIVE_TYPING_TIMEOUT_SECONDS
        < DEFAULT_TIMEOUT_SECONDS
    )
