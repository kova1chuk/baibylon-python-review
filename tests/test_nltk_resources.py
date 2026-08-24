import pytest

from app.services import nltk_resources


def test_nltk_resources_are_verified_without_runtime_download(monkeypatch) -> None:
    found: list[str] = []
    monkeypatch.setattr(nltk_resources, "_ready", False)
    monkeypatch.setattr(nltk_resources.nltk.data, "find", found.append)
    monkeypatch.setattr(
        nltk_resources.nltk,
        "download",
        lambda *_args, **_kwargs: pytest.fail("runtime download is forbidden"),
    )

    nltk_resources.ensure_nltk_data()

    assert found == list(nltk_resources._REQUIRED_RESOURCES)


def test_nltk_resources_fail_fast_when_image_is_incomplete(monkeypatch) -> None:
    monkeypatch.setattr(nltk_resources, "_ready", False)

    def missing(_resource: str) -> None:
        raise LookupError("missing immutable resource")

    monkeypatch.setattr(nltk_resources.nltk.data, "find", missing)

    with pytest.raises(LookupError, match="missing immutable resource"):
        nltk_resources.ensure_nltk_data()
