import router
from router import Route


def test_parse_plain_text_is_a_search() -> None:
    assert router.parse("aphex twin") == Route(text="aphex twin")


def test_parse_band_page_with_filter() -> None:
    parsed = router.parse("aphextwin.bandcamp.com > drukqs")
    assert parsed == Route(band="aphextwin.bandcamp.com", text="drukqs")


def test_parse_release_page_with_filter() -> None:
    parsed = router.parse("Band > Album > one > two")
    assert parsed == Route(band="Band", release="Album", text="one two")


def test_urls_round_trip_through_paths() -> None:
    url = "https://x.bandcamp.com/album/a?label=1"
    assert router.split_url(url) == ("x.bandcamp.com", "album/a")
    assert router.band_url("x.bandcamp.com") == "https://x.bandcamp.com"
    assert router.release_url("x.bandcamp.com", "album/a") == (
        "https://x.bandcamp.com/album/a"
    )


def test_drill_builds_readable_paths() -> None:
    assert router.drill("Band") == "Band > "
    assert router.drill("Band", "Album") == "Band > Album > "
    assert router.drill("A > B", "C  D") == "A - B > C D > "


def test_matches_requires_every_word() -> None:
    assert router.matches("ONE two", "Track one and Two")
    assert not router.matches("one three", "Track one and Two")
