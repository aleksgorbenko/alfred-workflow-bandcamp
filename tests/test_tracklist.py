from unittest.mock import patch

from bandcamp_api import BandcampError
from tracklist import build_items, main


@patch("tracklist.images.warm", return_value={})
def test_build_items_empty_tracklist_shows_message(_mock_warm):
    items = build_items({"trackinfo": []}, "https://x.bandcamp.com/album/a")
    assert len(items) == 1
    assert items[0]["valid"] is False


@patch("tracklist.images.warm", return_value={})
def test_build_items_track_rows_show_formatted_duration(_mock_warm):
    release = {
        "trackinfo": [{"title": "Track One", "track_num": 1, "duration": 143.88}]
    }
    result = build_items(release, "https://x.bandcamp.com/album/a")[0]
    assert "Track One" in result["title"]
    assert result["subtitle"] == "2:23"
    assert result["arg"] == "https://x.bandcamp.com/album/a"
    assert result["valid"] is True


@patch("tracklist.images.warm", return_value={})
def test_build_items_subtitle_includes_artist(_mock_warm):
    release = {
        "artist": "An Artist",
        "trackinfo": [{"title": "Track One", "duration": 100}],
    }
    result = build_items(release, "https://x.bandcamp.com/album/a")[0]
    assert result["subtitle"] == "1:40・An Artist"


@patch("tracklist.images.warm", return_value={})
def test_build_items_subtitle_includes_label_when_distinct_from_artist(_mock_warm):
    release = {
        "artist": "Flying Moth",
        "site_name": "Egoplanet",
        "trackinfo": [{"title": "Not Now", "duration": 100}],
    }
    result = build_items(release, "https://x.bandcamp.com/track/not-now")[0]
    assert result["subtitle"] == "1:40・Flying Moth・Egoplanet"


@patch("tracklist.images.warm", return_value={})
def test_build_items_subtitle_puts_year_before_artist_and_label(_mock_warm):
    release = {
        "artist": "Flying Moth",
        "site_name": "Egoplanet",
        "album_release_date": "11 Jul 2025 00:00:00 GMT",
        "trackinfo": [{"title": "Not Now", "duration": 100}],
    }
    result = build_items(release, "https://x.bandcamp.com/track/not-now")[0]
    assert result["subtitle"] == "1:40・2025・Flying Moth・Egoplanet"


@patch("tracklist.images.warm", return_value={})
def test_build_items_subtitle_includes_tags(_mock_warm):
    release = {
        "artist": "Aphex Twin",
        "tags": ["electronic", "IDM"],
        "trackinfo": [{"title": "Track One", "duration": 100}],
    }
    result = build_items(release, "https://x.bandcamp.com/album/a")[0]
    assert result["subtitle"] == "1:40・Aphex Twin・electronic, IDM"


@patch("tracklist.images.warm", return_value={})
def test_build_items_subtitle_caps_tags_at_three(_mock_warm):
    release = {
        "artist": "Aphex Twin",
        "tags": ["electronic", "IDM", "Experimental", "UK", "Braindance"],
        "trackinfo": [{"title": "Track One", "duration": 100}],
    }
    result = build_items(release, "https://x.bandcamp.com/album/a")[0]
    assert result["subtitle"] == "1:40・Aphex Twin・electronic, IDM, Experimental"


@patch("tracklist.images.warm", return_value={})
def test_build_items_subtitle_omits_label_when_same_as_artist(_mock_warm):
    release = {
        "artist": "Aphex Twin",
        "site_name": "Aphex Twin",
        "trackinfo": [{"title": "Track One", "duration": 100}],
    }
    result = build_items(release, "https://x.bandcamp.com/album/a")[0]
    assert result["subtitle"] == "1:40・Aphex Twin"


@patch("tracklist.images.warm", return_value={})
def test_build_items_subtitle_includes_year(_mock_warm):
    release = {
        "artist": "Aphex Twin",
        "album_release_date": "22 Oct 2001 00:00:00 GMT",
        "trackinfo": [{"title": "Track One", "duration": 100}],
    }
    result = build_items(release, "https://x.bandcamp.com/album/a")[0]
    assert result["subtitle"] == "1:40・2001・Aphex Twin"


@patch(
    "tracklist.images.warm",
    return_value={"https://f4.bcbits.com/img/a9_9.jpg": "/tmp/cover.jpg"},
)
def test_build_items_uses_release_cover_art_for_every_track(mock_warm):
    release = {
        "art_id": 9,
        "trackinfo": [
            {"title": "Track One", "duration": 100},
            {"title": "Track Two", "duration": 100},
        ],
    }
    rows = build_items(release, "https://x.bandcamp.com/album/a")
    assert all(row["icon"] == {"path": "/tmp/cover.jpg"} for row in rows)
    mock_warm.assert_called_once_with(["https://f4.bcbits.com/img/a9_9.jpg"])


@patch("tracklist.images.warm", return_value={})
def test_build_items_falls_back_to_track_icon_without_art_id(_mock_warm):
    release = {"trackinfo": [{"title": "Track One", "duration": 60}]}
    result = build_items(release, "https://x.bandcamp.com/album/a")[0]
    assert result["icon"] == {"path": "icons/icon_track.png"}


@patch.dict("os.environ", {}, clear=True)
def test_main_errors_when_no_selection(capsys):
    main()
    out = capsys.readouterr().out
    assert "selection" in out.lower()


@patch.dict("os.environ", {"BC_URL": "https://broken.bandcamp.com/album/a"}, clear=True)
@patch("tracklist.bandcamp_api.get_release", side_effect=BandcampError("boom"))
def test_main_surfaces_bandcamp_error(_mock_get, capsys):
    main()
    out = capsys.readouterr().out
    assert "boom" in out


@patch.dict("os.environ", {"BC_URL": "https://x.bandcamp.com/album/a"}, clear=True)
@patch("tracklist.images.warm", return_value={})
@patch("tracklist.bandcamp_api.get_release", return_value={"trackinfo": []})
def test_main_dispatches_with_bc_url(mock_get, _mock_warm):
    main()
    mock_get.assert_called_once_with("https://x.bandcamp.com/album/a")
