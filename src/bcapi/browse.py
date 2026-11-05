import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import bandcamp_api
import names
import router
from alfred_items import HINT_OPEN, TYPE_ICONS, item, open_mod, with_hint
from bandcamp_api import BandcampError

import images

TAG_LIMIT = 3
DETAIL_WORKERS = 8


def _icon_type(entry: dict[str, Any]) -> str:
    return "track" if entry.get("type") == "track" else "album"


def _title(entry: dict[str, Any]) -> str:
    artist = entry.get("artist")
    return f"{artist} - {entry['title']}" if artist else entry["title"]


def _absolute_url(band_url: str, page_url: str) -> str:
    return (
        page_url
        if page_url.startswith("http")
        else urllib.parse.urljoin(band_url, page_url)
    )


def _thumb_url(entry: dict[str, Any]) -> str | None:
    art_id = entry.get("art_id")
    return f"https://f4.bcbits.com/img/a{art_id}_9.jpg" if art_id else None


def _fetch_tags(urls: list[str]) -> dict[str, list[str]]:
    tags_by_url: dict[str, list[str]] = {}
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        future_to_url = {
            executor.submit(bandcamp_api.get_release, url): url for url in urls
        }
        for future, url in future_to_url.items():
            try:
                tags_by_url[url] = future.result().get("tags", [])
            except BandcampError:
                continue
    return tags_by_url


def _subtitle(entry: dict[str, Any], tags: list[str]) -> str:
    parts = [_icon_type(entry).title(), ", ".join(tags[:TAG_LIMIT])]
    return "・".join(part for part in parts if part)


def _owner(entry: dict[str, Any], page_url: str) -> str:
    return entry.get("artist") or router.split_url(page_url)[0]


def build_items(
    entries: list[dict[str, Any]], band: str, band_url: str
) -> list[dict[str, Any]]:
    if not entries:
        return [item(title="No releases found", valid=False)]

    thumbs = [_thumb_url(entry) for entry in entries]
    icons = images.warm(thumbs)
    page_urls = [_absolute_url(band_url, entry["page_url"]) for entry in entries]
    tags_by_url = _fetch_tags(page_urls)
    host = router.split_url(band_url)[0]
    owners = [
        band if router.split_url(page_url)[0] == host else _owner(entry, page_url)
        for entry, page_url in zip(entries, page_urls, strict=True)
    ]
    names.remember(
        {
            key: value
            for entry, page_url, owner in zip(entries, page_urls, owners, strict=True)
            for key, value in (
                (names.band_key(owner), router.split_url(page_url)[0]),
                (
                    names.release_key(router.split_url(page_url)[0], entry["title"]),
                    router.split_url(page_url)[1],
                ),
            )
        }
    )
    items: list[dict[str, Any]] = []
    for entry, thumb, page_url, owner in zip(
        entries, thumbs, page_urls, owners, strict=True
    ):
        items.append(
            item(
                title=_title(entry),
                subtitle=with_hint(
                    _subtitle(entry, tags_by_url.get(page_url, [])), HINT_OPEN
                ),
                valid=False,
                autocomplete=router.drill(owner, entry["title"]),
                icon=(icons.get(thumb) if thumb else None)
                or TYPE_ICONS[_icon_type(entry)],
                mods=open_mod(page_url),
            )
        )
    return items
