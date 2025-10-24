#!/usr/bin/env python3
"""
This script downloads the latest Secure Controls Framework (SCF) Excel file
from its official GitHub repository and saves it to /scf_full/scf_latest.xlsx.

It dynamically finds the .xlsx file in the repository, so it doesn't need
to be updated when a new version of the SCF is released.

Prerequisites:
- Python 3.10+
- uv (for environment and package management)
- Project dependencies. For a reproducible environment, it's best to
  compile a lock file and then sync from it:
  1. `uv pip compile requirements.txt -o requirements.lock`
  2. `uv pip sync requirements.lock`
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

import requests
from tqdm.auto import tqdm

# Import configuration
try:
    from logging_config import get_logger
    from constants import (
        GITHUB_REPO, GITHUB_API_URL, GITHUB_API_TIMEOUT,
        DOWNLOAD_TIMEOUT, DOWNLOAD_CHUNK_SIZE,
        SCF_EXCEL_FILENAME, SCF_SHA_FILENAME, SCF_VERSION_FILENAME
    )
    logger = get_logger(__name__)
except ImportError:
    # Fallback for standalone usage
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    GITHUB_REPO = "securecontrolsframework/securecontrolsframework"
    GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/"
    GITHUB_API_TIMEOUT = 15
    DOWNLOAD_TIMEOUT = 60
    DOWNLOAD_CHUNK_SIZE = 8192
    SCF_EXCEL_FILENAME = "scf_latest.xlsx"
    SCF_SHA_FILENAME = "scf_latest.sha"
    SCF_VERSION_FILENAME = "scf_latest.version"

def download_scf(dest_dir: Path, sha_file: Path, version_file: Path) -> None:
    """
    Downloads the latest SCF Excel file from GitHub.

    Args:
        dest_dir: Directory to save the downloaded file.
        sha_file: Path to store the SHA hash of the downloaded file.
        version_file: Path to store the version string.

    Raises:
        RuntimeError: If download fails or directories cannot be created.
    """
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"Error: Could not create destination directory {dest_dir}. Reason: {e}")

    dest_file = dest_dir / SCF_EXCEL_FILENAME

    # 1. Get remote file metadata from the GitHub API
    try:
        response = requests.get(GITHUB_API_URL, timeout=GITHUB_API_TIMEOUT)
        response.raise_for_status()
        repo_contents = response.json()

        excel_file_meta = next(
            (item for item in repo_contents if item['name'].endswith('.xlsx')),
            None
        )

        if not excel_file_meta:
            raise RuntimeError(f"Error: Could not find an .xlsx file in the repository at {GITHUB_API_URL}")

        remote_sha: str = excel_file_meta['sha']
        download_url: str = excel_file_meta['download_url']
        original_filename: str = excel_file_meta['name']
        # This regex is more flexible and doesn't require a leading 'v'.
        version_match = re.search(r'(\d{4}-\d+-\d+)', original_filename)
        remote_version: str = version_match.group(1).replace('-', '.') if version_match else "unknown"

        # 2. Compare with local SHA to see if a download is needed
        local_sha: str = ""
        if sha_file.is_file():
            local_sha = sha_file.read_text(encoding='utf-8').strip()

        if remote_sha == local_sha and dest_file.is_file():
            logger.info(f"SCF version is up to date ({local_sha[:7]}). No download needed.")
            return

        logger.info(f"Downloading new SCF version (remote: {remote_sha[:7]})...")

        # 3. Download the file with a progress bar
        try:
            with requests.get(download_url, stream=True, timeout=DOWNLOAD_TIMEOUT) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                with open(dest_file, 'wb') as f, tqdm(
                    desc=dest_file.name,
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar:
                    for chunk in r.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                        size = f.write(chunk)
                        bar.update(size)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Error during file download: {e}")

        # 4. Save the new SHA to the tracking file
        try:
            sha_file.write_text(remote_sha, encoding='utf-8')
        except Exception as e:
            raise RuntimeError(f"Error writing SHA file {sha_file}: {e}")

        # 5. Save the new version string to its own tracking file
        try:
            version_file.write_text(remote_version, encoding='utf-8')
        except Exception as e:
            raise RuntimeError(f"Error writing version file {version_file}: {e}")

        logger.info(f"Successfully downloaded new SCF version {remote_version}. Local SHA is now {remote_sha[:7]}.")

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"An error occurred during the GitHub API request: {e}")

def main() -> None:
    """Parses command-line arguments and initiates the download."""
    parser = argparse.ArgumentParser(
        description="Downloads the latest Secure Controls Framework (SCF) Excel file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path(__file__).parent / "scf_full",
        help="The destination directory for the downloaded file."
    )
    parser.add_argument(
        "--sha-file",
        type=Path,
        default=None,
        help="Path to SHA tracking file (default: output-dir/scf_latest.sha)"
    )
    parser.add_argument(
        "--version-file",
        type=Path,
        default=None,
        help="Path to version tracking file (default: output-dir/scf_latest.version)"
    )
    args = parser.parse_args()

    sha_file = args.sha_file or args.output_dir / SCF_SHA_FILENAME
    version_file = args.version_file or args.output_dir / SCF_VERSION_FILENAME

    download_scf(args.output_dir, sha_file, version_file)

if __name__ == "__main__":
    main()