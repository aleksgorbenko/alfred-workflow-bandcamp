import urllib.error
from unittest.mock import patch

import pytest
from bandcamp_api import (
    BandcampError,
    _extract_json_attr,
    _extract_meta_content,
    _extract_tags,
    get_band_releases,
    get_release,
    search,
)

MUSIC_GRID_HTML = (
    '<div id="music-grid" data-client-items="'
    "[{&quot;art_id&quot;:123,&quot;id&quot;:456,"
    "&quot;title&quot;:&quot;A Release&quot;,&quot;type&quot;:&quot;album&quot;,"
    "&quot;page_url&quot;:&quot;/album/a-release&quot;}]"
    '"></div>'
)

TRALBUM_HTML = (
    '<script data-tralbum="'
    "{&quot;artist&quot;:&quot;An Artist&quot;,&quot;trackinfo&quot;:"
    "[{&quot;title&quot;:&quot;Track One&quot;,&quot;track_num&quot;:1,"
    "&quot;duration&quot;:143.88,&quot;title_link&quot;:&quot;/track/track-one&quot;}]}"
    '"></script>'
)

RELEASE_PAGE_HTML = TRALBUM_HTML + '<meta property="og:site_name" content="A Label">'

TAGS_HTML = """
<div class="tralbumData tralbum-tags tralbum-tags-nu hidden">
    <h3><span class="tags-inline-label">Tags</span></h3>
    <a class="tag" href="https://bandcamp.com/discover/electronic?from=tralbum"
        >electronic</a>
    <a class="tag" href="https://bandcamp.com/discover/united-kingdom?from=tralbum"
        >United Kingdom</a>
</div>
"""

RELEASE_PAGE_WITH_TAGS_HTML = TRALBUM_HTML + TAGS_HTML


def test_extract_json_attr_parses_music_grid():
    result = _extract_json_attr(MUSIC_GRID_HTML, "data-client-items")
    assert result == [
        {
            "art_id": 123,
            "id": 456,
            "title": "A Release",
            "type": "album",
            "page_url": "/album/a-release",
        }
    ]


def test_extract_json_attr_parses_tralbum():
    result = _extract_json_attr(TRALBUM_HTML, "data-tralbum")
    assert result["artist"] == "An Artist"
    assert result["trackinfo"][0]["title"] == "Track One"


def test_extract_json_attr_raises_when_attribute_missing():
    with pytest.raises(BandcampError, match="data-client-items"):
        _extract_json_attr("<html><body>not found</body></html>", "data-client-items")


@patch("bandcamp_api.urllib.request.urlopen")
def test_search_sends_post_body_and_user_agent(mock_urlopen):
    payload = {"auto": {"results": []}}
    with patch("bandcamp_api.json.load", return_value=payload):
        search("aphex twin")

    request = mock_urlopen.call_args[0][0]
    assert request.full_url == (
        "https://bandcamp.com/api/bcsearch_public_api/1/autocomplete_elastic"
    )
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("User-agent")
    assert request.data is not None


@patch("bandcamp_api.urllib.request.urlopen")
def test_search_returns_results_list(_mock_urlopen):
    payload = {
        "auto": {
            "results": [
                {"type": "b", "name": "Aphex Twin", "item_url_root": "https://x"}
            ]
        }
    }
    with patch("bandcamp_api.json.load", return_value=payload):
        result = search("aphex twin")
    assert result == [{"type": "b", "name": "Aphex Twin", "item_url_root": "https://x"}]


@patch("bandcamp_api.urllib.request.urlopen")
def test_search_slices_to_per_page(_mock_urlopen):
    per_page = 3
    payload = {"auto": {"results": [{"id": i} for i in range(10)]}}
    with patch("bandcamp_api.json.load", return_value=payload):
        result = search("query", per_page=per_page)
    assert len(result) == per_page


@patch("bandcamp_api.urllib.request.urlopen")
def test_search_raises_bandcamp_error_on_http_error(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="", code=500, msg="Server Error", hdrs=None, fp=None
    )
    with pytest.raises(BandcampError):
        search("query")


@patch("bandcamp_api.urllib.request.urlopen")
def test_search_raises_bandcamp_error_on_url_error(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError("no network")
    with pytest.raises(BandcampError):
        search("query")


@patch("bandcamp_api._fetch_html", return_value=MUSIC_GRID_HTML)
def test_get_band_releases_returns_parsed_list(_mock_fetch):
    result = get_band_releases("https://aphextwin.bandcamp.com")
    assert result == [
        {
            "art_id": 123,
            "id": 456,
            "title": "A Release",
            "type": "album",
            "page_url": "/album/a-release",
        }
    ]


@patch("bandcamp_api._fetch_html")
def test_get_band_releases_is_cached_across_calls(mock_fetch):
    mock_fetch.return_value = MUSIC_GRID_HTML
    get_band_releases("https://cached-band.bandcamp.com")
    get_band_releases("https://cached-band.bandcamp.com")
    assert mock_fetch.call_count == 1


@patch("bandcamp_api._fetch_html", side_effect=BandcampError("boom"))
def test_get_band_releases_propagates_fetch_error(_mock_fetch):
    with pytest.raises(BandcampError, match="boom"):
        get_band_releases("https://broken.bandcamp.com")


def test_extract_meta_content_finds_og_site_name():
    result = _extract_meta_content(RELEASE_PAGE_HTML, "og:site_name")
    assert result == "A Label"


def test_extract_meta_content_returns_none_when_missing():
    result = _extract_meta_content("<html></html>", "og:site_name")
    assert result is None


def test_extract_tags_parses_tag_anchors():
    result = _extract_tags(RELEASE_PAGE_WITH_TAGS_HTML)
    assert result == ["electronic", "United Kingdom"]


def test_extract_tags_returns_empty_list_when_missing():
    result = _extract_tags(TRALBUM_HTML)
    assert result == []


@patch("bandcamp_api._fetch_html", return_value=RELEASE_PAGE_WITH_TAGS_HTML)
def test_get_release_includes_tags(_mock_fetch):
    result = get_release("https://artist.bandcamp.com/album/a-release")
    assert result["tags"] == ["electronic", "United Kingdom"]


@patch("bandcamp_api._fetch_html", return_value=TRALBUM_HTML)
def test_get_release_omits_tags_when_none_found(_mock_fetch):
    result = get_release("https://plain2.bandcamp.com/album/a-release")
    assert "tags" not in result


@patch("bandcamp_api._fetch_html", return_value=TRALBUM_HTML)
def test_get_release_returns_parsed_tralbum(_mock_fetch):
    result = get_release("https://artist.bandcamp.com/album/a-release")
    assert result["artist"] == "An Artist"
    assert len(result["trackinfo"]) == 1


@patch("bandcamp_api._fetch_html", return_value=RELEASE_PAGE_HTML)
def test_get_release_includes_site_name(_mock_fetch):
    result = get_release("https://label.bandcamp.com/album/a-release")
    assert result["site_name"] == "A Label"


@patch("bandcamp_api._fetch_html", return_value=TRALBUM_HTML)
def test_get_release_omits_site_name_when_meta_missing(_mock_fetch):
    result = get_release("https://plain.bandcamp.com/album/a-release")
    assert "site_name" not in result


@patch("bandcamp_api._fetch_html")
def test_get_release_is_cached_across_calls(mock_fetch):
    mock_fetch.return_value = TRALBUM_HTML
    get_release("https://cached-release.bandcamp.com/album/x")
    get_release("https://cached-release.bandcamp.com/album/x")
    assert mock_fetch.call_count == 1
