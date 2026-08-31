import os
import re
import sys

import bandcamp_api
import images
from alfred_items import emit, error_item, item
from bandcamp_api import BandcampError

TRACK_ICON = "icons/icon_track.png"
TAG_LIMIT = 3


def _duration(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


def _title(track: dict) -> str:
    track_num = track.get("track_num")
    return f"{track_num}. {track['title']}" if track_num else track["title"]


def _year(date_str: str | None) -> str:
    match = re.search(r"\d{4}", date_str or "")
    return match.group(0) if match else ""


def _release_subtitle(release: dict) -> str:
    artist = release.get("artist") or ""
    site_name = release.get("site_name") or ""
    label = site_name if site_name and site_name != artist else ""
    tags = ", ".join((release.get("tags") or [])[:TAG_LIMIT])
    parts = [_year(release.get("album_release_date")), artist, label, tags]
    return "・".join(part for part in parts if part)


def _cover_icon(release: dict) -> str:
    art_id = release.get("art_id")
    if not art_id:
        return TRACK_ICON
    thumb = f"https://f4.bcbits.com/img/a{art_id}_9.jpg"
    return images.warm([thumb]).get(thumb) or TRACK_ICON


def build_items(release: dict, release_url: str) -> list[dict]:
    tracklist = release.get("trackinfo", [])
    if not tracklist:
        return [item(title="No tracklist available", valid=False)]

    icon = _cover_icon(release)
    release_subtitle = _release_subtitle(release)
    return [
        item(
            title=_title(track),
            subtitle="・".join(
                part
                for part in (_duration(track.get("duration") or 0), release_subtitle)
                if part
            ),
            arg=release_url,
            icon=icon,
        )
        for track in tracklist
    ]


def main() -> None:
    bc_url = os.environ.get("BC_URL", "")
    if not bc_url:
        emit([error_item("No selection to browse")])
        return

    try:
        release = bandcamp_api.get_release(bc_url)
    except BandcampError as error:
        emit([error_item(str(error))])
        return

    emit(build_items(release, bc_url))


if __name__ == "__main__":
    sys.exit(main())
