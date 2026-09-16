"""Filesystem TTL cleanup for user experiment directories."""

import time
import shutil
import logging
from pathlib import Path
from app.config import settings

logger = logging.getLogger("flycast.jobs.cleanup")


def cleanup_expired_experiments(ttl_hours: int = 24) -> int:
    """Removes experiment directories older than ttl_hours."""
    exp_dir = settings.experiments_dir
    if not exp_dir.exists():
        return 0

    now = time.time()
    cutoff_seconds = ttl_hours * 3600
    removed_count = 0

    for item in exp_dir.iterdir():
        if item.is_dir():
            try:
                # Check directory mtime
                mtime = item.stat().st_mtime
                if (now - mtime) > cutoff_seconds:
                    logger.info("Purging expired experiment directory: %s", item.name)
                    shutil.rmtree(item, ignore_errors=True)
                    removed_count += 1
            except Exception as e:
                logger.warning("Error inspecting experiment dir %s: %s", item.name, e)

    return removed_count
