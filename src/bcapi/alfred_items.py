import json
import sys

TYPE_ICONS = {
    "band": "icons/icon_band.png",
    "label": "icons/icon_label.png",
    "album": "icons/icon_album.png",
    "track": "icons/icon_track.png",
}


def item(
    title: str,
    subtitle: str = "",
    arg: str | None = None,
    valid: bool = True,
    icon: str | None = None,
    variables: dict[str, str] | None = None,
) -> dict:
    result: dict = {"title": title, "subtitle": subtitle, "valid": valid}
    if arg is not None:
        result["arg"] = arg
    if icon is not None:
        result["icon"] = {"path": icon}
    if variables is not None:
        result["variables"] = variables
    return result


def error_item(message: str) -> dict:
    return item(title=message, valid=False)


def emit(items: list[dict]) -> None:
    json.dump({"items": items}, sys.stdout)
