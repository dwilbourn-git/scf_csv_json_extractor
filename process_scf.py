#!/usr/bin/env python3
"""
This script reads the SCF Excel workbook and splits each worksheet into a
separate CSV file, making the data easier to work with.

It can be configured to ignore specific sheets.
"""

import argparse
import re
import sys
import warnings
from pathlib import Path
from typing import Optional

import pandas as pd
from tqdm.auto import tqdm

# Import configuration
try:
    from logging_config import get_logger
    from constants import SCF_EXCEL_FILENAME, SCF_SHA_FILENAME, CSV_VERSION_TRACKING
    logger = get_logger(__name__)
except ImportError:
    # Fallback for standalone usage
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    SCF_EXCEL_FILENAME = "scf_latest.xlsx"
    SCF_SHA_FILENAME = "scf_latest.sha"
    CSV_VERSION_TRACKING = ".version.sha"

def sanitize_filename(name: str) -> str:
    """
    Cleans a string to be a valid filename, removing common version/date suffixes.

    Examples:
        - "Mappings - NIST 800-53 R5" -> "Mappings_NIST_800_53"
        - "Release Notes 2024.1"      -> "Release_Notes"
    """
    # Remove common versioning patterns like " R5", " 2022", " v1.2" from the end.
    name_no_version = re.sub(r'\s+(R\d+|v\d+|\d{4})(\.\d+)*$', '', name, flags=re.IGNORECASE).strip()

    # Replace any non-alphanumeric characters with a single underscore.
    sane_name = re.sub(r'[^a-zA-Z0-9]+', '_', name_no_version)

    # Remove any leading/trailing underscores.
    return sane_name.strip('_')

def split_workbook_to_csv(excel_file: Path, source_sha_file: Path, output_dir: Path, ignore_sheets: list[str]) -> None:
    """
    Reads an Excel workbook and saves each sheet as a separate CSV file.

    Args:
        excel_file: Path to the input .xlsx file.
        source_sha_file: Path to the source .sha file to check for new versions.
        output_dir: Directory to save the output CSV files.
        ignore_sheets: A list of sheet names to ignore (case-insensitive).

    Raises:
        RuntimeError: If the Excel file is not found, directories cannot be created,
                     or there are errors processing the workbook.
    """
    if not excel_file.is_file():
        raise RuntimeError(f"Error: Input Excel file not found at '{excel_file}'. Hint: Have you run the 'download_scf.py' script first?")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"Error: Could not create output directory '{output_dir}'. Reason: {e}")

    # --- Version Check Logic ---
    tracking_sha_file = output_dir / CSV_VERSION_TRACKING
    if not source_sha_file.is_file():
        raise RuntimeError(f"Error: Source SHA file not found at '{source_sha_file}'. Hint: Run the download step first.")

    source_sha: str = source_sha_file.read_text(encoding='utf-8').strip()
    processed_sha: str = ""
    if tracking_sha_file.is_file():
        processed_sha = tracking_sha_file.read_text(encoding='utf-8').strip()

    if source_sha == processed_sha:
        logger.info(f"Raw CSVs are already up to date (version {source_sha[:7]}).")
        return

    logger.info(f"Source data has been updated (new version {source_sha[:7]}). Processing into CSVs...")
    # --- End Version Check ---

    # Use pd.ExcelFile for efficiency. We also suppress a known, benign UserWarning
    # from openpyxl about "Data Validation extension" to keep the output clean.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
        try:
            xls = pd.ExcelFile(excel_file)
        except Exception as e:
            raise RuntimeError(f"Error opening Excel file {excel_file}: {e}")

    ignore_sheets_lower: list[str] = [sheet.lower() for sheet in ignore_sheets]

    # Wrap the sheet processing loop with tqdm for a progress bar
    for sheet_name in tqdm(xls.sheet_names, desc="Processing sheets", unit="sheet"):
        if sheet_name.lower() in ignore_sheets_lower:
            # This sheet is ignored, so we just continue to the next one.
            # No need to print anything as the progress bar shows activity.
            continue

        # Read all data as strings to prevent automatic type conversion (e.g., "5.10" -> 5.1).
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, dtype=str)
        except Exception as e:
            logger.warning(f"Could not read sheet '{sheet_name}' from '{excel_file}'. Skipping. Error: {e}")
            continue

        safe_filename: str = sanitize_filename(sheet_name)
        csv_path: Path = output_dir / f"{safe_filename}.csv"

        # Save the DataFrame to a CSV file, without the pandas index column.
        try:
            df.to_csv(csv_path, index=False, encoding='utf-8')
        except Exception as e:
            raise RuntimeError(f"Error saving CSV to {csv_path}: {e}")

    logger.info(f"\nSuccessfully processed workbook. Raw CSV files are in '{output_dir}'")

    # Write the new sha to the tracking file to mark this version as processed.
    try:
        tracking_sha_file.write_text(source_sha, encoding='utf-8')
    except Exception as e:
        raise RuntimeError(f"Error writing tracking SHA file {tracking_sha_file}: {e}")
    logger.info(f"Updated CSV version tracking to {source_sha[:7]}.")

def main() -> None:
    """Parses command-line arguments and initiates the splitting process."""
    parser = argparse.ArgumentParser(
        description="Splits each worksheet of an Excel file into a separate CSV.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i", "--input-file",
        type=Path,
        default=Path(__file__).parent / "scf_full" / SCF_EXCEL_FILENAME,
        help="The source .xlsx file to process."
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path(__file__).parent / "csv",
        help="The destination directory for the output CSV files."
    )
    parser.add_argument(
        "--source-sha-file",
        type=Path,
        default=Path(__file__).parent / "scf_full" / SCF_SHA_FILENAME,
        help="The source .sha file to check for new versions."
    )
    parser.add_argument("--ignore", nargs='+', default=["Lists"], help="Space-separated list of sheet names to ignore.")
    args = parser.parse_args()

    split_workbook_to_csv(args.input_file, args.source_sha_file, args.output_dir, args.ignore)

if __name__ == "__main__":
    main()