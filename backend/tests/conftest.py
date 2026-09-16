"""Pytest configuration and shared fixtures."""

import os
import shutil
import tempfile
from pathlib import Path
import pytest
import numpy as np
import scipy.sparse as sp

# Set environment before loading application
os.environ["USE_FIXTURE_BRAIN"] = "true"
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="flycast_test_data_")

from app.config import settings
from app.brain.fixture import save_fixture_to_disk
from app.brain.loader import load_brain, BrainState


@pytest.fixture(scope="session", autouse=True)
def setup_test_brain():
    """Generates and loads test fixture connectome."""
    test_brain_dir = settings.brain_dir
    save_fixture_to_disk(test_brain_dir, num_neurons=100, seed=42)
    brain = load_brain(test_brain_dir, force_reload=True)
    yield brain
    # Teardown
    shutil.rmtree(settings.DATA_DIR, ignore_errors=True)


@pytest.fixture
def brain_state(setup_test_brain) -> BrainState:
    return setup_test_brain
