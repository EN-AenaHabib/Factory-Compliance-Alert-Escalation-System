"""
scripts/download_dataset.py

Automatically downloads the factory safe/unsafe behaviour video dataset
from Kaggle (https://www.kaggle.com/datasets/trnhhnggiang/videodataset-for-
safe-and-unsafe-behaviours) and stages the clips into data/raw_clips/.

Kaggle requires a personal API token (KAGGLE_USERNAME / KAGGLE_KEY) for any
programmatic access — this is a platform-level requirement, not something
any client library can remove. Once that token is set in .env, this script
runs with zero further manual steps: setup.sh calls it automatically.

Run directly:
    python3 scripts/download_dataset.py
"""
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.config import load_config, resolve_path
from src.common.logging_utils import get_logger

logger = get_logger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}


def _stage_clips(source_dir: Path, dest_dir: Path) -> int:
    dest_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in source_dir.rglob("*"):
        if path.suffix.lower() in VIDEO_EXTENSIONS:
            target = dest_dir / path.name
            if not target.exists():
                shutil.copy2(path, target)
            count += 1
    return count


def download_dataset(config: dict | None = None) -> bool:
    """Returns True if clips are available in data/raw_clips/ after this
    call (whether freshly downloaded or already present), False otherwise."""
    cfg = config or load_config()
    ds_cfg = cfg["dataset"]
    raw_clips_dir = resolve_path(cfg["paths"]["raw_clips_dir"])

    existing = [
        p for p in raw_clips_dir.rglob("*") if p.suffix.lower() in VIDEO_EXTENSIONS
    ]
    if existing:
        logger.info(
            f"{len(existing)} clip(s) already present in {raw_clips_dir}, "
            f"skipping download."
        )
        return True

    if not ds_cfg.get("auto_download", True):
        logger.warning("auto_download disabled in config.yaml — skipping.")
        return False

    kaggle_username = os.environ.get("KAGGLE_USERNAME")
    kaggle_key = os.environ.get("KAGGLE_KEY")

    if not kaggle_username or not kaggle_key:
        msg = (
            "KAGGLE_USERNAME / KAGGLE_KEY not set. Kaggle requires a "
            "personal API token for programmatic dataset access (see "
            "https://www.kaggle.com/settings -> API). Set these in .env "
            "and re-run, or place clips manually in "
            f"{raw_clips_dir}."
        )
        if ds_cfg.get("allow_offline_fallback", True):
            logger.warning(msg + " Continuing with offline fallback (no clips found).")
            return False
        else:
            raise RuntimeError(msg)

    try:
        import kagglehub
    except ImportError as e:
        raise RuntimeError(
            "kagglehub is not installed. Run `pip install -r requirements.txt`."
        ) from e

    handle = ds_cfg["kaggle_handle"]
    logger.info(f"Downloading Kaggle dataset '{handle}' (one-time, cached locally)...")
    download_path = kagglehub.dataset_download(handle)
    logger.info(f"Kaggle dataset cached at: {download_path}")

    count = _stage_clips(Path(download_path), raw_clips_dir)
    if count == 0:
        logger.warning(
            f"No video files found under {download_path}. The dataset "
            f"layout may differ from expected — inspect it manually."
        )
        return False

    logger.info(f"Staged {count} clip(s) into {raw_clips_dir}")
    return True


if __name__ == "__main__":
    ok = download_dataset()
    sys.exit(0 if ok else 1)
