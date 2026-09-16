"""CLI tool to build or inspect the MaleCNS connectome artifacts."""

import sys
import logging
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.brain.bootstrap import bootstrap_brain
from app.brain.loader import is_brain_ready, get_brain

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("flycast.build_brain")

def main():
    force = "--force" in sys.argv
    logger.info("Checking connectome in %s (force=%s)...", settings.brain_dir, force)
    bootstrap_brain(force=force)

    if is_brain_ready():
        brain = get_brain()
        logger.info("Brain successfully verified!")
        logger.info("Dataset: %s", brain.manifest.dataset)
        logger.info("Neurons: %d (published: %d)", brain.num_neurons, brain.manifest.published_neurons)
        logger.info("Edges: %d", brain.num_edges)
        logger.info("Sensory input neurons: %d", len(brain.input_indices))
        logger.info("Readout electrodes: %d", len(brain.readout_indices))
    else:
        logger.error("Brain is not ready after build.")
        sys.exit(1)

if __name__ == "__main__":
    main()
