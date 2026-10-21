from alfred_items import TYPE_ICONS, item


def test_item_omits_icon_by_default() -> None:
    assert "icon" not in item(title="Title")


def test_item_wraps_icon_path_in_alfred_icon_object() -> None:
    result = item(title="Title", icon="icons/icon_album.png")
    assert result["icon"] == {"path": "icons/icon_album.png"}


def test_type_icons_covers_all_result_types() -> None:
    assert set(TYPE_ICONS) == {"band", "label", "album", "track"}


def test_item_omits_variables_by_default() -> None:
    assert "variables" not in item(title="Title")


def test_item_includes_variables_when_given() -> None:
    result = item(
        title="Title", variables={"BC_TYPE": "release", "BC_URL": "https://x"}
    )
    assert result["variables"] == {"BC_TYPE": "release", "BC_URL": "https://x"}
