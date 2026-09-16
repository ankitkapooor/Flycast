"""Unit tests for safe Feather reader and connectome manifest validation."""

import json
from pathlib import Path
import pytest
import pyarrow as pa
import pyarrow.feather as feather
import polars as pl
from unittest.mock import patch

from app.brain.feather_reader import read_feather_safe, decode_arrow_column
from app.brain.loader import is_brain_ready
from app.brain.manifest import ConnectomeManifest
from app.brain.bootstrap import bootstrap_brain
from app.brain.fixture import save_fixture_to_disk
from app.config import settings


def test_read_feather_safe_negative_index_dictionary(tmp_path: Path):
    """Verifies that Feather files containing -1 dictionary keys fail with standard Polars IPC

    reader but are successfully parsed by read_feather_safe.
    """
    feather_file = tmp_path / "legacy_annotations.feather"

    # Create signed int32 indices containing [0, -1, 1]
    indices = pa.py_buffer(b"\x00\x00\x00\x00\xff\xff\xff\xff\x01\x00\x00\x00")
    dictionary = pa.array(["DN1p", "MBON01"])
    dict_arr = pa.DictionaryArray.from_buffers(
        pa.dictionary(pa.int32(), pa.string()), 3, [None, indices], dictionary
    )

    id_arr = pa.array([10001, 10002, 10003], type=pa.int64())
    normal_str = pa.array(["left", "right", None], type=pa.string())

    table = pa.table({
        "bodyId": id_arr,
        "type": dict_arr,
        "side": normal_str,
    })
    feather.write_feather(table, feather_file)

    # 1. Verify standard Polars IPC reader fails with ComputeError
    with pytest.raises(Exception) as exc_info:
        pl.read_ipc(feather_file)
    assert "-1" in str(exc_info.value) or "usize" in str(exc_info.value)

    # 2. Verify read_feather_safe reads and decodes cleanly
    df = read_feather_safe(feather_file)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 3
    assert df.columns == ["bodyId", "type", "side"]
    assert df["bodyId"].to_list() == [10001, 10002, 10003]
    assert df["type"].to_list() == ["DN1p", None, "MBON01"]
    assert df["side"].to_list() == ["left", "right", None]
    assert df["type"].dtype == pl.String


def test_decode_arrow_column_chunked():
    """Verifies decode_arrow_column works properly on ChunkedArray with out-of-bounds / negative values."""
    indices_buf = pa.py_buffer(b"\x00\x00\x00\x00\xff\xff\xff\xff")  # [0, -1]
    dictionary = pa.array(["glutamatergic"])
    dict_arr1 = pa.DictionaryArray.from_buffers(
        pa.dictionary(pa.int32(), pa.string()), 2, [None, indices_buf], dictionary
    )
    chunked = pa.chunked_array([dict_arr1, dict_arr1])

    decoded = decode_arrow_column(chunked)
    assert isinstance(decoded, pa.ChunkedArray)
    assert decoded.to_pylist() == ["glutamatergic", None, "glutamatergic", None]


def test_is_brain_ready_rejects_fixture_when_require_real(tmp_path: Path):
    """Verifies that is_brain_ready rejects synthetic fixtures when require_real=True."""
    brain_dir = tmp_path / "brain"
    save_fixture_to_disk(brain_dir, num_neurons=20, seed=42)

    # Brain is ready for fixture mode
    assert is_brain_ready(brain_dir, require_real=False) is True

    # Brain is NOT ready if real connectome is required
    assert is_brain_ready(brain_dir, require_real=True) is False


def test_is_brain_ready_accepts_real_manifest(tmp_path: Path):
    """Verifies that is_brain_ready accepts a real MaleCNS manifest."""
    brain_dir = tmp_path / "brain"
    save_fixture_to_disk(brain_dir, num_neurons=20, seed=42)

    # Overwrite manifest to simulate real build
    manifest_path = brain_dir / "manifest.json"
    with open(manifest_path, "r") as f:
        data = json.load(f)

    data["is_fixture"] = False
    data["brain_mode"] = "real"
    data["dataset"] = "male-cns:v1.0"

    with open(manifest_path, "w") as f:
        json.dump(data, f)

    assert is_brain_ready(brain_dir, require_real=True) is True


def test_bootstrap_purges_stale_fixture_in_production(tmp_path: Path, monkeypatch):
    """Verifies that bootstrap_brain purges stale fixture directories when USE_FIXTURE_BRAIN=False."""
    brain_dir = tmp_path / "brain"
    save_fixture_to_disk(brain_dir, num_neurons=20, seed=42)

    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "USE_FIXTURE_BRAIN", False)
    monkeypatch.setattr(settings, "ALLOW_FIXTURE_FALLBACK", False)

    # Mock download_source_file to raise an error so we can check that stale fixture was purged
    with patch("app.brain.bootstrap.download_source_file", side_effect=RuntimeError("Simulated download error")):
        with pytest.raises(RuntimeError, match="Simulated download error"):
            bootstrap_brain()

    # The stale fixture should have been removed
    assert not brain_dir.exists()


def test_bootstrap_fixture_fallback_toggles(tmp_path: Path, monkeypatch):
    """Verifies that ALLOW_FIXTURE_FALLBACK controls fallback behavior on build error."""
    brain_dir = tmp_path / "brain"
    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "USE_FIXTURE_BRAIN", False)

    # Case 1: ALLOW_FIXTURE_FALLBACK is False -> raises exception
    monkeypatch.setattr(settings, "ALLOW_FIXTURE_FALLBACK", False)
    with patch("app.brain.bootstrap.download_source_file", side_effect=RuntimeError("Build failure")):
        with pytest.raises(RuntimeError, match="Build failure"):
            bootstrap_brain()
    assert not brain_dir.exists()

    # Case 2: ALLOW_FIXTURE_FALLBACK is True -> falls back to fixture
    monkeypatch.setattr(settings, "ALLOW_FIXTURE_FALLBACK", True)
    with patch("app.brain.bootstrap.download_source_file", side_effect=RuntimeError("Build failure")):
        bootstrap_brain()
    assert brain_dir.exists()
    assert (brain_dir / "manifest.json").exists()
    with open(brain_dir / "manifest.json") as f:
        m = json.load(f)
    assert m["is_fixture"] is True
