from typing import Any

import names
import router
from alfred_items import HINT_OPEN, TYPE_ICONS, item, open_mod, with_hint

import images

_SUBTITLES = {"a": "Album", "t": "Track"}
LIVE_TYPING_TIMEOUT_SECONDS = 2
TAG_LIMIT = 3


def _icon_type(entry: dict[str, Any]) -> str:
    if entry["type"] == "b":
        return "label" if entry.get("is_label") else "band"
    return "album" if entry["type"] == "a" else "track"


def _title(entry: dict[str, Any]) -> str:
    band_name = entry.get("band_name")
    return f"{band_name} - {entry['name']}" if band_name else entry["name"]


def _tags(entry: dict[str, Any]) -> str:
    tags: list[Any] = entry.get("tag_names") or []
    return ", ".join(tags[:TAG_LIMIT])


def _subtitle(entry: dict[str, Any]) -> str:
    if entry["type"] == "b":
        return "Label" if entry.get("is_label") else "Band"
    parts = [_SUBTITLES[entry["type"]], _tags(entry)]
    return "・".join(part for part in parts if part)


def _url(entry: dict[str, Any]) -> str:
    return entry.get("item_url_path") or entry["item_url_root"]


def _drill(entry: dict[str, Any]) -> str:
    host, release = router.split_url(_url(entry))
    if entry["type"] == "b":
        names.remember({names.band_key(entry["name"]): host})
        return router.drill(entry["name"])
    band = entry.get("band_name") or host
    names.remember(
        {
            names.band_key(band): host,
            names.release_key(host, entry["name"]): release,
        }
    )
    return router.drill(band, entry["name"])


def build_items(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not entries:
        return [item(title="No results on Bandcamp", valid=False)]

    icons = images.warm(
        [entry.get("img") for entry in entries],
        timeout_seconds=LIVE_TYPING_TIMEOUT_SECONDS,
    )
    return [
        item(
            title=_title(entry),
            subtitle=with_hint(_subtitle(entry), HINT_OPEN),
            valid=False,
            autocomplete=_drill(entry),
            icon=icons.get(entry.get("img") or "") or TYPE_ICONS[_icon_type(entry)],
            mods=open_mod(_url(entry)),
        )
        for entry in entries
    ]
