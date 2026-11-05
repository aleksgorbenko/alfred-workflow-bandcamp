from dataclasses import dataclass
from urllib.parse import urlparse

SEPARATOR = ">"


@dataclass(frozen=True)
class Route:
    text: str = ""
    band: str = ""
    release: str = ""


def parse(query: str) -> Route:
    parts = [part.strip() for part in query.split(SEPARATOR)]
    if len(parts) == 1:
        return Route(text=parts[0])
    if len(parts) == 2:  # noqa: PLR2004
        return Route(band=parts[0], text=parts[1])
    return Route(band=parts[0], release=parts[1], text=" ".join(parts[2:]))


def clean(name: str) -> str:
    return " ".join(name.replace(SEPARATOR, "-").split())


def band_url(host: str) -> str:
    return f"https://{host}"


def release_url(host: str, release: str) -> str:
    return f"https://{host}/{release}"


def split_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    return parsed.netloc, parsed.path.strip("/")


def drill(band: str, release: str = "") -> str:
    path = f"{clean(band)} {SEPARATOR} "
    return f"{path}{clean(release)} {SEPARATOR} " if release else path


def matches(text: str, title: str) -> bool:
    words = text.lower().split()
    haystack = title.lower()
    return all(word in haystack for word in words)
