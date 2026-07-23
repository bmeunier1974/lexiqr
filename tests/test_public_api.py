"""The public API surface: `from lexiqr import EntityResolver` (ADR 0002)."""


def test_entity_resolver_is_importable_from_the_package_root() -> None:
    from lexiqr import EntityResolver

    assert EntityResolver is not None
