import os
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import bandcamp_api
import images
from alfred_items import TYPE_ICONS, emit, error_item, item
from bandcamp_api import BandcampError

TAG_LIMIT = 3
DETAIL_WORKERS = 8


def _icon_type(entry: dict) -> str:
    return "track" if entry.get("type") == "track" else "album"


def _title(entry: dict) -> str:
    artist = entry.get("artist")
    return f"{artist} - {entry['title']}" if artist else entry["title"]


def _absolute_url(band_url: str, page_url: str) -> str:
    return (
        page_url
        if page_url.startswith("http")
        else urllib.parse.urljoin(band_url, page_url)
    )


def _thumb_url(entry: dict) -> str | None:
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


def _subtitle(entry: dict, tags: list[str]) -> str:
    parts = [_icon_type(entry).title(), ", ".join(tags[:TAG_LIMIT])]
    return "・".join(part for part in parts if part)


def build_items(entries: list[dict], band_url: str) -> list[dict]:
    if not entries:
        return [item(title="No releases found", valid=False)]

    thumbs = [_thumb_url(entry) for entry in entries]
    icons = images.warm(thumbs)
    page_urls = [_absolute_url(band_url, entry["page_url"]) for entry in entries]
    tags_by_url = _fetch_tags(page_urls)
    items = []
    for entry, thumb, page_url in zip(entries, thumbs, page_urls, strict=True):
        items.append(
            item(
                title=_title(entry),
                subtitle=_subtitle(entry, tags_by_url.get(page_url, [])),
                arg=page_url,
                icon=icons.get(thumb) or TYPE_ICONS[_icon_type(entry)],
                variables={"BC_TYPE": "release", "BC_URL": page_url},
            )
        )
    return items


def main() -> None:
    bc_type = os.environ.get("BC_TYPE", "")
    bc_url = os.environ.get("BC_URL", "")
    if bc_type != "band" or not bc_url:
        emit([error_item("No selection to browse")])
        return

    try:
        entries = bandcamp_api.get_band_releases(bc_url)
    except BandcampError as error:
        emit([error_item(str(error))])
        return

    emit(build_items(entries, bc_url))


if __name__ == "__main__":
    sys.exit(main())
