"""Regression tests for issue #13: --store-key must work on a virgin install.

When config.txt is missing or empty, `dat --store-key` should prompt for a
key (or accept one via --key) and write it, not crash while trying to read
the file first.
"""
import importlib.resources
import sys
from pathlib import Path

import pytest

from dehashapitool import run


@pytest.fixture
def config_path():
    return Path(str(importlib.resources.files("dehashapitool") / "config.txt"))


@pytest.fixture
def preserve_config(config_path):
    original = config_path.read_text() if config_path.exists() else None
    try:
        yield config_path
    finally:
        if original is None:
            config_path.unlink(missing_ok=True)
        else:
            config_path.write_text(original)


def test_store_key_with_empty_config(preserve_config, monkeypatch):
    preserve_config.write_text("")
    monkeypatch.setattr(sys, "argv", ["dat", "--store-key", "--key", "TESTKEY", "--email", "x@y.z"])

    args = run.load_args()

    assert args.dehashed_key == "TESTKEY"
    assert preserve_config.read_text().strip() == "TESTKEY"


def test_store_key_with_missing_config(preserve_config, monkeypatch):
    preserve_config.unlink(missing_ok=True)
    monkeypatch.setattr(sys, "argv", ["dat", "--store-key", "--key", "TESTKEY", "--email", "x@y.z"])

    args = run.load_args()

    assert args.dehashed_key == "TESTKEY"
    assert preserve_config.read_text().strip() == "TESTKEY"
