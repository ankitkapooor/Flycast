"""Bootstrap script for acquiring and processing the MaleCNS v1.0 connectome.

Supports atomic build, anonymous Google Cloud Storage download, and fallback to fixture mode.
Run directly via:
    python -m app.brain.bootstrap
"""

import os
import json
import shutil
import logging
import urllib.request
from pathlib import Path
from typing import Optional

from app.config import settings
from app.brain.manifest import ConnectomeManifest
from app.brain.preprocess import process_malecns_data
from app.brain.fixture import save_fixture_to_disk
from app.brain.loader import is_brain_ready

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("flycast.brain.bootstrap")

GCS_BUCKET = "flyem-male-cns"
GCS_PREFIX = "v1.0/connectome-data/flat-connectome"
HTTP_BASE_URL = f"https://storage.googleapis.com/{GCS_BUCKET}/{GCS_PREFIX}"

REQUIRED_SOURCE_FILES = {
    "weights": "connectome-weights-male-cns-v1.0-minconf-0.5.feather",
    "annotations": "body-annotations-male-cns-v1.0-minconf-0.5.feather",
    "neurotransmitters": "body-neurotransmitters-male-cns-v1.0.feather",
}


def download_source_file(filename: str, target_dir: Path) -> Path:
    """Downloads a single source file from GCS using anonymous access or public HTTPS."""
    target_path = target_dir / filename
    if target_path.exists() and target_path.stat().st_size > 1000:
        logger.info("Found cached raw file %s (%d bytes)", filename, target_path.stat().st_size)
        return target_path

    logger.info("Downloading %s ...", filename)
    target_dir.mkdir(parents=True, exist_ok=True)

    # Try anonymous gcsfs first if available
    try:
        import gcsfs
        fs = gcsfs.GCSFileSystem(anon=True)
        gcs_source = f"{GCS_BUCKET}/{GCS_PREFIX}/{filename}"
        logger.info("Fetching gs://%s via anonymous gcsfs...", gcs_source)
        fs.get(gcs_source, str(target_path))
        if target_path.exists() and target_path.stat().st_size > 1000:
            return target_path
    except Exception as gcs_err:
        logger.warning("gcsfs download failed (%s). Falling back to direct public HTTPS...", gcs_err)

    # Fallback to direct HTTPS download
    url = f"{HTTP_BASE_URL}/{filename}"
    logger.info("Downloading from URL: %s", url)
    urllib.request.urlretrieve(url, str(target_path))
    return target_path


def bootstrap_brain(force: bool = False) -> None:
    """Ensures a valid runtime brain exists in settings.brain_dir."""
    brain_dir = settings.brain_dir

    if not force and is_brain_ready(brain_dir):
        logger.info("Connectome already prepared and verified at %s. Skipping bootstrap.", brain_dir)
        return

    # Check if fixture brain is requested via environment
    if settings.USE_FIXTURE_BRAIN:
        logger.info("USE_FIXTURE_BRAIN is active. Creating synthetic Drosophila CNS fixture at %s", brain_dir)
        save_fixture_to_disk(brain_dir, num_neurons=300, seed=settings.CONNECTOME_SEED)
        return

    # If brain_dir exists but is not ready (e.g. stale fixture in production), purge it
    if brain_dir.exists() and not settings.USE_FIXTURE_BRAIN:
        manifest_path = brain_dir / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r") as f:
                    m_data = json.load(f)
                if m_data.get("is_fixture") or m_data.get("brain_mode") != "real" or "fixture" in str(m_data.get("dataset", "")).lower():
                    logger.warning(
                        "Detected stale synthetic fixture brain at %s while USE_FIXTURE_BRAIN=false. "
                        "Purging stale fixture to force real MaleCNS connectome build.",
                        brain_dir,
                    )
                    shutil.rmtree(brain_dir, ignore_errors=True)
            except Exception as read_err:
                logger.warning("Could not inspect existing manifest at %s: %s", manifest_path, read_err)

    # Atomic building directory
    building_dir = brain_dir.parent / f"{brain_dir.name}.building"
    if building_dir.exists():
        shutil.rmtree(building_dir)
    building_dir.mkdir(parents=True, exist_ok=True)

    # Temporary directory for 1.1GB raw files
    tmp_raw_dir = Path("/tmp/malecns")
    tmp_raw_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info("Initiating MaleCNS v1.0 acquisition...")
        weights_path = download_source_file(REQUIRED_SOURCE_FILES["weights"], tmp_raw_dir)
        annotations_path = download_source_file(REQUIRED_SOURCE_FILES["annotations"], tmp_raw_dir)
        
        nt_path = None
        try:
            nt_path = download_source_file(REQUIRED_SOURCE_FILES["neurotransmitters"], tmp_raw_dir)
        except Exception as nt_err:
            logger.warning("Optional neurotransmitters file could not be downloaded: %s", nt_err)

        logger.info("Processing MaleCNS connectome into CSR sparse arrays...")
        process_malecns_data(
            weights_feather_path=weights_path,
            annotations_feather_path=annotations_path,
            neurotransmitters_feather_path=nt_path,
            output_dir=building_dir,
            seed=settings.CONNECTOME_SEED,
            num_input_neurons=settings.INPUT_NEURONS,
            num_readout_neurons=settings.READOUT_NEURONS,
            sign_mode=settings.CONNECTOME_SIGN_MODE,
        )

        # Atomic rename: building_dir -> brain_dir
        if brain_dir.exists():
            shutil.rmtree(brain_dir)
        building_dir.rename(brain_dir)
        logger.info("Successfully installed MaleCNS connectome to %s", brain_dir)

        try:
            with open(brain_dir / "manifest.json", "r") as f:
                manifest_dict = json.load(f)
            logger.info(
                "MaleCNS Connectome Manifest:\n"
                "  Dataset: %s\n"
                "  Status: %s (is_fixture=%s)\n"
                "  Runtime Neurons: %d\n"
                "  Runtime Edges: %d\n"
                "  CSR Shape: %s\n"
                "  CSR Nonzero Count: %d\n"
                "  Input Neurons: %d\n"
                "  Readout Neurons: %d",
                manifest_dict.get("dataset"),
                manifest_dict.get("brain_mode"),
                manifest_dict.get("is_fixture"),
                manifest_dict.get("neurons"),
                manifest_dict.get("edges"),
                tuple(manifest_dict.get("csr_shape", [])),
                manifest_dict.get("csr_nonzero_count", manifest_dict.get("edges")),
                manifest_dict.get("num_input_neurons"),
                manifest_dict.get("num_readout_neurons"),
            )
        except Exception as log_err:
            logger.warning("Failed to log manifest summary: %s", log_err)

    except Exception as e:
        logger.error("Failed to build real MaleCNS connectome: %s", e, exc_info=True)
        if settings.ALLOW_FIXTURE_FALLBACK:
            logger.warning("ALLOW_FIXTURE_FALLBACK is true. Falling back to synthetic fixture connectome...")
            save_fixture_to_disk(brain_dir, num_neurons=300, seed=settings.CONNECTOME_SEED)
        else:
            logger.error("ALLOW_FIXTURE_FALLBACK is false. Aborting connectome bootstrap without fallback.")
            raise e

    finally:
        # Cleanup ephemeral raw files
        if tmp_raw_dir.exists() and not os.environ.get("KEEP_RAW_CONNECTOME"):
            logger.info("Cleaning up temporary raw files in %s", tmp_raw_dir)
            shutil.rmtree(tmp_raw_dir, ignore_errors=True)
        if building_dir.exists():
            shutil.rmtree(building_dir, ignore_errors=True)


if __name__ == "__main__":
    bootstrap_brain()
