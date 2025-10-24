#!/usr/bin/env python3
"""
This script queries and displays the version of the downloaded SCF file.
"""

import argparse
import sys
from pathlib import Path
from typing import NoReturn

# Import configuration
try:
    from logging_config import get_logger
    from constants import SCF_VERSION_FILENAME
    logger = get_logger(__name__)
except ImportError:
    # Fallback for standalone usage
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    SCF_VERSION_FILENAME = "scf_latest.version"

def query_scf_version(version_file: Path) -> None:
    """
    Reads the version file and displays the formatted version string.

    Args:
        version_file: Path to the version file.

    Raises:
        SystemExit: If the version file is not found, is empty, or contains "unknown".
    """
    if not version_file.is_file():
        logger.error(f"Version file not found at '{version_file}'.")
        logger.error("Hint: Run the pipeline to download the SCF data first.")
        sys.exit(1)

    version: str = version_file.read_text(encoding='utf-8').strip()
    if not version:
        logger.error(f"Version file '{version_file}' is empty.")
        sys.exit(1)

    if version == "unknown":
        logger.error("Could not determine version from remote filename. Check download logs.")
        sys.exit(1)

    logger.info(f"The version of the SCF in this model is {version}")

def main() -> None:
    """Parses command-line arguments and initiates the query."""
    parser = argparse.ArgumentParser(description="Queries the version of the downloaded SCF file.")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path(__file__).parent / "scf_full" / SCF_VERSION_FILENAME,
        help="Path to the SCF version file."
    )
    args = parser.parse_args()
    query_scf_version(args.file)

if __name__ == "__main__":
    main()