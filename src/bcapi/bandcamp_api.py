import html
import json
import re
import urllib.error
import urllib.request
from typing import Any

from cache import cached
from sqlite_cache import cached_sqlite

API_BASE = "https://bandcamp.com/api/bcsearch_public_api/1/autocomplete_elastic"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

ONE_HOUR = 3600
ONE_MONTH = 2592000

_ATTR_PATTERN = '{attr}="([^"]*)"'


class BandcampError(Exception):
    pass


def _fetch_html(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        msg = f"Bandcamp returned HTTP {error.code} for {url}"
        raise BandcampError(msg) from error
    except urllib.error.URLError as error:
        msg = f"Could not reach Bandcamp ({url}): {error.reason}"
        raise BandcampError(msg) from error


def extract_json_attr(page_html: str, attr_name: str) -> Any:  # noqa: ANN401
    match = re.search(_ATTR_PATTERN.format(attr=attr_name), page_html)
    if not match:
        msg = f"Could not find {attr_name} on the page"
        raise BandcampError(msg)
    return json.loads(html.unescape(match.group(1)))


def extract_meta_content(page_html: str, property_name: str) -> str | None:
    pattern = rf'<meta property="{re.escape(property_name)}" content="([^"]*)">'
    match = re.search(pattern, page_html)
    return html.unescape(match.group(1)) if match else None


def extract_tags(page_html: str) -> list[str]:
    matches = re.findall(r'<a class="tag"[^>]*>\s*([^<]+?)\s*</a>', page_html)
    return [html.unescape(tag) for tag in matches]


def search(query: str, per_page: int = 20) -> list[dict[str, Any]]:
    body = json.dumps(
        {"search_text": query, "search_filter": "", "full_page": True}
    ).encode()
    request = urllib.request.Request(
        API_BASE,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )

    def fetch() -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
                return json.load(response)
        except urllib.error.HTTPError as error:
            msg = f"Bandcamp search returned HTTP {error.code}"
            raise BandcampError(msg) from error
        except urllib.error.URLError as error:
            msg = f"Could not reach Bandcamp: {error.reason}"
            raise BandcampError(msg) from error

    cache_key = f"{API_BASE}?q={query}"
    results = cached(cache_key, ONE_HOUR, fetch)["auto"]["results"]
    return results[:per_page]


def get_band_releases(band_url: str) -> list[dict[str, Any]]:
    def fetch() -> list[dict[str, Any]]:
        page_html = _fetch_html(band_url)
        return extract_json_attr(page_html, "data-client-items")

    return cached_sqlite(band_url, ONE_MONTH, fetch)


def get_release(release_url: str) -> dict[str, Any]:
    def fetch() -> dict[str, Any]:
        page_html = _fetch_html(release_url)
        tralbum = extract_json_attr(page_html, "data-tralbum")
        site_name = extract_meta_content(page_html, "og:site_name")
        if site_name:
            tralbum["site_name"] = site_name
        tags = extract_tags(page_html)
        if tags:
            tralbum["tags"] = tags
        return tralbum

    return cached_sqlite(release_url, ONE_MONTH, fetch)
