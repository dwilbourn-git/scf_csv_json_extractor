#!/usr/bin/env python3
"""
This script converts cleaned CSV files to JSON format for easier consumption
by APIs, web applications, and other tools.
"""

import argparse
import json
from pathlib import Path
from typing import Optional

import pandas as pd

# Import configuration
try:
    from logging_config import get_logger
    from constants import SCF_CSV_FILENAME
    logger = get_logger(__name__)
except ImportError:
    # Fallback for standalone usage
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    SCF_CSV_FILENAME = "SCF.csv"


def convert_csv_to_json(csv_path: Path, json_path: Path, orient: str = "records") -> None:
    """
    Converts a single CSV file to JSON format.

    Args:
        csv_path: Path to the input CSV file.
        json_path: Path to the output JSON file.
        orient: JSON orientation format (records, index, columns, values, table).
                Default is 'records' which creates an array of objects.

    Raises:
        RuntimeError: If the CSV cannot be read or JSON cannot be written.
    """
    try:
        # Read CSV with all data as strings to preserve formatting
        df = pd.read_csv(csv_path, dtype=str, encoding='utf-8')

        # Replace NaN values with None for proper JSON null representation
        df = df.where(pd.notna(df), None)

        # Convert to JSON
        json_data = df.to_dict(orient=orient)

        # Write with proper formatting
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        logger.info(f"  - Converted {csv_path.name} ({len(df)} rows)")

    except Exception as e:
        raise RuntimeError(f"Error converting {csv_path.name} to JSON: {e}")


def export_to_json(
    csv_dir: Path,
    json_dir: Path,
    include_relationships: bool = True,
    scf_rel_dir: Optional[Path] = None,
    framework_rel_dir: Optional[Path] = None,
    selected_frameworks: Optional[list[str]] = None
) -> None:
    """
    Exports all cleaned CSV files to JSON format.

    Args:
        csv_dir: Directory containing cleaned CSV files.
        json_dir: Directory to save JSON files.
        include_relationships: Whether to also export relationship files.
        scf_rel_dir: Directory containing SCF relationship CSVs (required if include_relationships is True).
        framework_rel_dir: Directory containing framework relationship CSVs (required if include_relationships is True).
        selected_frameworks: List of framework IDs to include (e.g., ['scf_to_nist_800_53_rev5']). None means all frameworks.

    Raises:
        RuntimeError: If required directories don't exist or conversion fails.
    """
    if not csv_dir.is_dir():
        raise RuntimeError(f"CSV directory not found: {csv_dir}")

    # Create output directory
    json_dir.mkdir(exist_ok=True)

    logger.info(f"Exporting cleaned CSV files to JSON format...")

    # Convert main CSV files
    csv_files = sorted(csv_dir.glob("*.csv"))
    if not csv_files:
        logger.warning(f"No CSV files found in {csv_dir}")
        return

    converted_count = 0
    for csv_file in csv_files:
        json_file = json_dir / f"{csv_file.stem}.json"
        convert_csv_to_json(csv_file, json_file)
        converted_count += 1

    logger.info(f"Converted {converted_count} main CSV file(s) to JSON")

    # Convert relationship files if requested
    if include_relationships:
        if scf_rel_dir and scf_rel_dir.is_dir():
            scf_json_dir = json_dir / "scf_relationships"
            scf_json_dir.mkdir(exist_ok=True)

            scf_rel_files = sorted(scf_rel_dir.glob("*.csv"))
            rel_count = 0
            for csv_file in scf_rel_files:
                json_file = scf_json_dir / f"{csv_file.stem}.json"
                convert_csv_to_json(csv_file, json_file)
                rel_count += 1

            logger.info(f"Converted {rel_count} SCF relationship file(s) to JSON")

        if framework_rel_dir and framework_rel_dir.is_dir():
            fw_json_dir = json_dir / "framework_relationships"
            fw_json_dir.mkdir(exist_ok=True)

            fw_rel_files = sorted(framework_rel_dir.glob("*.csv"))

            # Filter frameworks if selection was provided
            if selected_frameworks:
                logger.info(f"Filtering to {len(selected_frameworks)} selected frameworks...")
                fw_rel_files = [f for f in fw_rel_files if f.stem in selected_frameworks]

            fw_count = 0
            for csv_file in fw_rel_files:
                json_file = fw_json_dir / f"{csv_file.stem}.json"
                convert_csv_to_json(csv_file, json_file)
                fw_count += 1

            logger.info(f"Converted {fw_count} framework relationship file(s) to JSON")

    logger.info(f"\nJSON export complete. Files saved to '{json_dir}'")


def main() -> None:
    """Parses command-line arguments and initiates JSON export."""
    parser = argparse.ArgumentParser(
        description="Converts cleaned CSV files to JSON format.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=Path("csv_cleaned"),
        help="Directory containing cleaned CSV files"
    )
    parser.add_argument(
        "--json-dir",
        type=Path,
        default=Path("json_output"),
        help="Directory to save JSON files"
    )
    parser.add_argument(
        "--include-relationships",
        action="store_true",
        default=True,
        help="Also export relationship files to JSON"
    )
    parser.add_argument(
        "--scf-rel-dir",
        type=Path,
        default=Path("scf_relationships"),
        help="Directory containing SCF relationship files"
    )
    parser.add_argument(
        "--framework-rel-dir",
        type=Path,
        default=Path("framework_relationships"),
        help="Directory containing framework relationship files"
    )

    args = parser.parse_args()

    export_to_json(
        args.csv_dir,
        args.json_dir,
        args.include_relationships,
        args.scf_rel_dir,
        args.framework_rel_dir
    )


if __name__ == "__main__":
    main()
