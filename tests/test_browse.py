from unittest.mock import patch

from bandcamp_api import BandcampError
from browse import build_items, main


@patch("browse.images.warm", return_value={})
def test_build_items_empty_list_shows_message(_mock_warm):
    items = build_items([], "https://aphextwin.bandcamp.com")
    assert len(items) == 1
    assert items[0]["valid"] is False


@patch("browse.bandcamp_api.get_release", return_value={})
@patch("browse.images.warm", return_value={})
def test_build_items_resolves_relative_page_url_against_band_url(
    _mock_warm, _mock_get_release
):
    entries = [{"id": 1, "title": "A Release", "type": "album", "page_url": "/album/a"}]
    result = build_items(entries, "https://aphextwin.bandcamp.com")[0]
    assert result["arg"] == "https://aphextwin.bandcamp.com/album/a"
    assert result["variables"] == {
        "BC_TYPE": "release",
        "BC_URL": "https://aphextwin.bandcamp.com/album/a",
    }


@patch("browse.bandcamp_api.get_release", return_value={})
@patch("browse.images.warm", return_value={})
def test_build_items_keeps_absolute_page_url_as_is(_mock_warm, _mock_get_release):
    entries = [
        {
            "id": 1,
            "title": "A Release",
            "type": "album",
            "artist": "Some Artist",
            "page_url": "https://someartist.bandcamp.com/album/a?label=1",
        }
    ]
    result = build_items(entries, "https://warprecords.bandcamp.com")[0]
    assert result["arg"] == "https://someartist.bandcamp.com/album/a?label=1"
    assert result["title"] == "Some Artist - A Release"


@patch("browse.bandcamp_api.get_release", return_value={})
@patch(
    "browse.images.warm",
    return_value={"https://f4.bcbits.com/img/a123_9.jpg": "/tmp/a.jpg"},
)
def test_build_items_constructs_thumb_from_art_id(mock_warm, _mock_get_release):
    entries = [
        {
            "id": 1,
            "title": "A Release",
            "type": "album",
            "art_id": 123,
            "page_url": "/x",
        }
    ]
    result = build_items(entries, "https://band.bandcamp.com")[0]
    assert result["icon"] == {"path": "/tmp/a.jpg"}
    mock_warm.assert_called_once_with(["https://f4.bcbits.com/img/a123_9.jpg"])


@patch("browse.bandcamp_api.get_release", return_value={})
@patch("browse.images.warm", return_value={})
def test_build_items_falls_back_to_type_icon_without_art_id(
    _mock_warm, _mock_get_release
):
    entries = [{"id": 1, "title": "A Track", "type": "track", "page_url": "/y"}]
    result = build_items(entries, "https://band.bandcamp.com")[0]
    assert result["icon"] == {"path": "icons/icon_track.png"}


@patch("browse.bandcamp_api.get_release", return_value={})
@patch("browse.images.warm", return_value={})
def test_build_items_subtitle_shows_album_type(_mock_warm, _mock_get_release):
    entries = [{"id": 1, "title": "A Release", "type": "album", "page_url": "/x"}]
    result = build_items(entries, "https://band.bandcamp.com")[0]
    assert result["subtitle"] == "Album"


@patch("browse.bandcamp_api.get_release", return_value={})
@patch("browse.images.warm", return_value={})
def test_build_items_subtitle_shows_track_type(_mock_warm, _mock_get_release):
    entries = [{"id": 1, "title": "A Track", "type": "track", "page_url": "/y"}]
    result = build_items(entries, "https://band.bandcamp.com")[0]
    assert result["subtitle"] == "Track"


@patch("browse.bandcamp_api.get_release", return_value={"tags": ["Electronic", "IDM"]})
@patch("browse.images.warm", return_value={})
def test_build_items_subtitle_includes_tags(_mock_warm, mock_get_release):
    entries = [{"id": 1, "title": "A Release", "type": "album", "page_url": "/x"}]
    result = build_items(entries, "https://band.bandcamp.com")[0]
    assert result["subtitle"] == "Album・Electronic, IDM"
    mock_get_release.assert_called_once_with("https://band.bandcamp.com/x")


@patch(
    "browse.bandcamp_api.get_release",
    return_value={"tags": ["Electronic", "IDM", "Experimental", "UK", "Braindance"]},
)
@patch("browse.images.warm", return_value={})
def test_build_items_subtitle_caps_tags_at_three(_mock_warm, _mock_get_release):
    entries = [{"id": 1, "title": "A Release", "type": "album", "page_url": "/x"}]
    result = build_items(entries, "https://band.bandcamp.com")[0]
    assert result["subtitle"] == "Album・Electronic, IDM, Experimental"


@patch("browse.bandcamp_api.get_release", side_effect=BandcampError("boom"))
@patch("browse.images.warm", return_value={})
def test_build_items_falls_back_when_tag_fetch_fails(_mock_warm, _mock_get_release):
    entries = [{"id": 1, "title": "A Release", "type": "album", "page_url": "/x"}]
    result = build_items(entries, "https://band.bandcamp.com")[0]
    assert result["subtitle"] == "Album"


@patch.dict("os.environ", {}, clear=True)
def test_main_errors_when_no_selection(capsys):
    main()
    out = capsys.readouterr().out
    assert "selection" in out.lower()


@patch.dict(
    "os.environ",
    {"BC_TYPE": "band", "BC_URL": "https://broken.bandcamp.com"},
    clear=True,
)
@patch("browse.bandcamp_api.get_band_releases", side_effect=BandcampError("boom"))
def test_main_surfaces_bandcamp_error(_mock_get, capsys):
    main()
    out = capsys.readouterr().out
    assert "boom" in out


@patch.dict(
    "os.environ",
    {"BC_TYPE": "band", "BC_URL": "https://band.bandcamp.com"},
    clear=True,
)
@patch("browse.images.warm", return_value={})
@patch("browse.bandcamp_api.get_band_releases", return_value=[])
def test_main_dispatches_with_bc_url(mock_get, _mock_warm):
    main()
    mock_get.assert_called_once_with("https://band.bandcamp.com")
