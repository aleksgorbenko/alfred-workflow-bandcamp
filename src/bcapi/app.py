import json
import sys
from typing import Any

import bandcamp_api
import browse
import names
import router
import search
import tracklist
from alfred_items import HINT_HEADER, error_item, item, with_hint
from async_view import finish, job_command, serve, settle
from bandcamp_api import BandcampError
from cache import cache_dir
from router import Route

Row = dict[str, Any]


def _header(title: str, subtitle: str, url: str, back: str) -> Row:
    return item(
        title=title,
        subtitle=with_hint(subtitle, HINT_HEADER),
        arg=url,
        autocomplete=back,
    )


def _filtered(rows: list[Row], text: str, kind: str) -> list[Row]:
    kept = [row for row in rows if router.matches(text, row["title"])]
    return kept or [item(title=f"No {kind} matches '{text}'", valid=False)]


def _search(text: str) -> list[Row]:
    if not text:
        return [item(title="Type to search Bandcamp…", valid=False)]
    return search.build_items(bandcamp_api.search(text))


def _band_host(name: str) -> str:
    host = names.recall(names.band_key(name))
    if host:
        return host
    bands = [entry for entry in bandcamp_api.search(name) if entry["type"] == "b"]
    exact = [entry for entry in bands if entry["name"].casefold() == name.casefold()]
    found = (exact or bands)[:1]
    if not found:
        msg = f"Could not find a Bandcamp page for '{name}'"
        raise BandcampError(msg)
    return router.split_url(found[0]["item_url_root"])[0]


def _release_path(host: str, title: str) -> str:
    path = names.recall(names.release_key(host, title))
    if path:
        return path
    entries = bandcamp_api.get_band_releases(router.band_url(host))
    for entry in entries:
        if entry["title"].casefold() == title.casefold():
            return router.split_url(entry["page_url"])[1]
    msg = f"Could not find '{title}' on {host}"
    raise BandcampError(msg)


def _releases(route: Route) -> list[Row]:
    url = router.band_url(_band_host(route.band))
    entries = bandcamp_api.get_band_releases(url)
    header = _header(route.band, "Releases", url, "")
    rows = browse.build_items(entries, route.band, url)
    return (
        [header, *_filtered(rows, route.text, "release")]
        if route.text
        else [
            header,
            *rows,
        ]
    )


def _tracks(route: Route) -> list[Row]:
    host = _band_host(route.band)
    url = router.release_url(host, _release_path(host, route.release))
    release = bandcamp_api.get_release(url)
    current: dict[str, Any] = release.get("current") or {}
    title: str = current.get("title") or route.release
    header = _header(
        title,
        tracklist.release_subtitle(release),
        url,
        router.drill(route.band),
    )
    rows = tracklist.build_items(release, url)
    return (
        [header, *_filtered(rows, route.text, "track")]
        if route.text
        else [
            header,
            *rows,
        ]
    )


def run(query: str) -> list[Row]:
    route = router.parse(query.strip())
    if not route.band:
        return _search(route.text)
    if not route.release:
        return _releases(route)
    return _tracks(route)


def loading_label(query: str) -> str:
    route = router.parse(query.strip())
    if not route.band:
        return f"Searching Bandcamp for '{route.text}'…"
    if not route.release:
        return f"Loading {route.band} releases…"
    return f"Loading {route.release} tracks…"


def _payload(query: str) -> dict[str, Any]:
    try:
        return {"items": run(query)}
    except BandcampError as error:
        return {"items": [error_item(str(error))]}


def _job(query: str) -> None:
    if not settle(cache_dir(), query):
        return
    try:
        payload = _payload(query)
    except Exception as error:  # noqa: BLE001
        payload = {"items": [error_item(str(error))]}
    finish(cache_dir(), query, payload)


def main(argv: list[str]) -> None:
    if argv[:1] == ["--job"]:
        _job(argv[1] if len(argv) > 1 else "")
        return
    query = argv[0] if argv else ""
    payload = (
        serve(
            query,
            directory=cache_dir(),
            command=job_command(__file__, query),
            label=loading_label(query),
        )
        if query.strip()
        else _payload(query)
    )
    json.dump(payload, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
