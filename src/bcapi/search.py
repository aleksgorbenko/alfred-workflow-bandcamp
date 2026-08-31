import sys

import bandcamp_api
import images
from alfred_items import TYPE_ICONS, emit, error_item, item
from bandcamp_api import BandcampError

_SUBTITLES = {"a": "Album", "t": "Track"}
LIVE_TYPING_TIMEOUT_SECONDS = 2
TAG_LIMIT = 3


def _icon_type(entry: dict) -> str:
    if entry["type"] == "b":
        return "label" if entry.get("is_label") else "band"
    return "album" if entry["type"] == "a" else "track"


def _title(entry: dict) -> str:
    band_name = entry.get("band_name")
    return f"{band_name} - {entry['name']}" if band_name else entry["name"]


def _tags(entry: dict) -> str:
    tags = entry.get("tag_names") or []
    return ", ".join(tags[:TAG_LIMIT])


def _subtitle(entry: dict) -> str:
    if entry["type"] == "b":
        return "Label" if entry.get("is_label") else "Band"
    parts = [_SUBTITLES[entry["type"]], _tags(entry)]
    return "・".join(part for part in parts if part)


def _bc_type(entry: dict) -> str:
    return "band" if entry["type"] == "b" else "release"


def _url(entry: dict) -> str:
    return entry.get("item_url_path") or entry["item_url_root"]


def build_items(entries: list[dict]) -> list[dict]:
    if not entries:
        return [item(title="No results on Bandcamp", valid=False)]

    icons = images.warm(
        [entry.get("img") for entry in entries],
        timeout_seconds=LIVE_TYPING_TIMEOUT_SECONDS,
    )
    return [
        item(
            title=_title(entry),
            subtitle=_subtitle(entry),
            arg=_url(entry),
            icon=icons.get(entry.get("img")) or TYPE_ICONS[_icon_type(entry)],
            variables={"BC_TYPE": _bc_type(entry), "BC_URL": _url(entry)},
        )
        for entry in entries
    ]


def main(argv: list[str]) -> None:
    query = argv[0].strip() if argv else ""
    if not query:
        emit([item(title="Type to search Bandcamp…", valid=False)])
        return

    try:
        entries = bandcamp_api.search(query)
    except BandcampError as error:
        emit([error_item(str(error))])
        return

    emit(build_items(entries))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
