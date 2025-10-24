#!/usr/bin/env python3
"""
This script validates the integrity of the generated data files.
It primarily checks for "broken links" in relationship files, ensuring that
all foreign keys point to a valid primary key in a corresponding entity file.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from tqdm.auto import tqdm

# Import configuration
try:
    from logging_config import get_logger
    from constants import ENTITY_CONFIG, RELATIONSHIP_FK_MAP
    logger = get_logger(__name__)
except ImportError:
    # Fallback for standalone usage
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    # Fallback configuration
    ENTITY_CONFIG = {
        'scf': ('SCF.csv', 'scf_id'),
        'assessment_objective': ('Assessment_Objectives.csv', 'scf_ao_id'),
        'data_privacy': ('Data_Privacy_Mgmt_Principles.csv', 'index'),
        'domain': ('SCF_Domains_Principles.csv', 'scf_identifier'),
        'erl': ('Evidence_Request_List.csv', 'erl_id'),
        'risk': ('Risk_Catalog.csv', 'risk_id'),
        'threat': ('Threat_Catalog.csv', 'threat_id'),
    }
    RELATIONSHIP_FK_MAP = {
        'scf_id': 'scf',
        'scf_ao_id': 'assessment_objective',
        'data_privacy_id': 'data_privacy',
        'scf_identifier': 'domain',
        'erl_id': 'erl',
        'risk_id': 'risk',
        'threat_id': 'threat',
    }

def load_primary_keys(file_path: Path, key_col: str) -> set[str]:
    """
    Loads a set of unique primary keys from a given file and column.

    Args:
        file_path: Path to the CSV file containing the primary keys.
        key_col: Name of the column containing the primary keys.

    Returns:
        A set of unique primary key values. Returns empty set if file not found or column missing.
    """
    if not file_path.is_file():
        tqdm.write(f"  - Info: Source file not found at '{file_path.name}'. Cannot load keys for '{key_col}'.")
        return set()
    try:
        df = pd.read_csv(file_path, usecols=[key_col], dtype=str, encoding='utf-8')
        return set(df[key_col].dropna())
    except (FileNotFoundError, KeyError, ValueError) as e:
        logger.warning(f"Could not load key '{key_col}' from '{file_path.name}'. Reason: {e}")
        return set()

def report_broken_links(rel_file_name: str, column: str, source_file_name: str, broken_links: set[str]) -> None:
    """
    Logs formatted error messages for a set of broken links.

    Args:
        rel_file_name: Name of the relationship file with broken links.
        column: Name of the column containing broken foreign keys.
        source_file_name: Name of the source file that should contain the referenced IDs.
        broken_links: Set of IDs that don't exist in the source file.
    """
    logger.error(f"\nERROR in '{rel_file_name}': Found {len(broken_links)} broken link(s) in column '{column}'.")
    # Show a few examples
    for link in list(broken_links)[:3]:
        logger.error(f"  - ID '{link}' does not exist in {source_file_name}")
    if len(broken_links) > 3:
        logger.error(f"  - ... and {len(broken_links) - 3} more.")

def validate_data(cleaned_dir: Path, scf_rel_dir: Path, framework_rel_dir: Path) -> int:
    """
    Orchestrates the validation process by loading primary keys and checking
    all relationship files against them.

    Args:
        cleaned_dir: Directory containing cleaned entity CSV files.
        scf_rel_dir: Directory containing SCF relationship files.
        framework_rel_dir: Directory containing framework relationship files.

    Returns:
        Total number of validation errors found.
    """
    error_count: int = 0

    # 1. Load all known primary keys from entity files into a cache.
    logger.info("Loading primary keys from all known entity files...")
    key_cache: dict[str, set[str]] = {}
    for key_name, (file_name, key_col) in tqdm(ENTITY_CONFIG.items(), desc="Loading Keys", unit="file"):
        key_cache[key_name] = load_primary_keys(cleaned_dir / file_name, key_col)
    logger.info("  - Key loading complete.")

    # Exit if the main SCF IDs could not be loaded, as all validation depends on it.
    if not key_cache.get('scf'):
        logger.error("\nError: Could not load primary keys from SCF.csv. Aborting validation.")
        # Return 1 to indicate a fatal error to the calling main function.
        return 1

    # 2. Gather all relationship files.
    relationship_files: list[Path] = list(scf_rel_dir.glob("*.csv")) + list(framework_rel_dir.glob("*.csv"))

    if not relationship_files:
        logger.warning("No relationship files found to validate.")
        return 0

    logger.info(f"\nChecking {len(relationship_files)} relationship files for broken links...")

    # 3. Iterate and validate each file.
    for rel_file in tqdm(relationship_files, desc="Validating files", unit="file"):
        try:
            df_rel = pd.read_csv(rel_file, dtype=str, encoding='utf-8')

            for col in df_rel.columns:
                # Check if the column is a known foreign key
                if col not in RELATIONSHIP_FK_MAP:
                    continue

                logical_key_name: str = RELATIONSHIP_FK_MAP[col]
                valid_keys: Optional[set[str]] = key_cache.get(logical_key_name)

                # Ensure the keys for this relationship type were loaded
                if not valid_keys:
                    # A warning would have been printed during key loading.
                    continue

                current_ids: set[str] = set(df_rel[col].dropna())
                broken_links: set[str] = current_ids - valid_keys

                if broken_links:
                    error_count += len(broken_links)
                    source_file_name, _ = ENTITY_CONFIG[logical_key_name]
                    report_broken_links(rel_file.name, col, source_file_name, broken_links)

        except Exception as e:
            error_count += 1
            logger.error(f"\nERROR: Could not process file '{rel_file.name}'. Reason: {e}")

    return error_count

def main() -> None:
    """Parses arguments and orchestrates the validation process."""
    parser = argparse.ArgumentParser(description="Validates the integrity of generated data files.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--cleaned-dir", type=Path, default=Path("csv_cleaned"), help="Directory containing the cleaned entity CSV files.")
    parser.add_argument("--scf-rel-dir", type=Path, default=Path("scf_relationships"), help="Directory containing the core SCF relationship files.")
    parser.add_argument("--framework-rel-dir", type=Path, default=Path("framework_relationships"), help="Directory containing the framework-to-control relationship files.")
    args = parser.parse_args()

    total_errors: int = validate_data(args.cleaned_dir, args.scf_rel_dir, args.framework_rel_dir)

    if total_errors == 0:
        logger.info("\nValidation successful. No broken links found.")
    else:
        logger.error(f"\nValidation failed. Found {total_errors} total error(s).")
        sys.exit(1)

if __name__ == "__main__":
    main()