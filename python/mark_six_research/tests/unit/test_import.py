def test_package_imports() -> None:
    import mark_six

    assert mark_six.__version__ == "0.1.0"
