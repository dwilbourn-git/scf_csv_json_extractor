#!/usr/bin/env python3
"""
This script reads the cleaned CSV files and generates relationship mapping
files suitable for import into a relational or graph database.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from clean_csv import to_snake_case

# Import configuration
try:
    from logging_config import get_logger
    from constants import (
        SCF_CSV_FILENAME, DATA_PRIVACY_CSV_FILENAME,
        COLUMN_REGISTER_FILENAME, DOMAIN_ID_LENGTH
    )
    logger = get_logger(__name__)
except ImportError:
    # Fallback for standalone usage
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    SCF_CSV_FILENAME = "SCF.csv"
    DATA_PRIVACY_CSV_FILENAME = "Data_Privacy_Mgmt_Principles.csv"
    COLUMN_REGISTER_FILENAME = "column_register.csv"
    DOMAIN_ID_LENGTH = 3

def create_relationship_file(df: pd.DataFrame, id_col: str, source_col: str, dest_col: str, output_path: Path) -> None:
    """
    Creates a two-column mapping file from a source DataFrame by exploding
    a delimited column.

    Args:
        df: The source DataFrame (e.g., controls).
        id_col: The primary ID column (e.g., 'scf_id').
        source_col: The column containing values to be split and exploded.
        dest_col: The desired name for the second column in the output file.
        output_path: The path to save the resulting CSV file.
    """
    if source_col not in df.columns:
        logger.warning(f"Column '{source_col}' not found. Skipping relationship.")
        return

    logger.info(f"  - Creating relationship from '{source_col}'...")

    # Select the two columns and drop rows with no mappings
    df_rel: pd.DataFrame = df[[id_col, source_col]].dropna(subset=[source_col]).copy()

    # Split values by newline and explode into separate rows
    df_rel[source_col] = df_rel[source_col].astype(str).str.split('\n')
    df_rel = df_rel.explode(source_col)

    # Clean up whitespace and remove any empty rows that result from splitting
    df_rel[source_col] = df_rel[source_col].str.strip()
    df_rel = df_rel[df_rel[source_col] != '']

    # Rename the source column to the desired destination column name for clarity
    df_rel.rename(columns={source_col: dest_col}, inplace=True)

    # Save to CSV
    df_rel.to_csv(output_path, index=False, encoding='utf-8')
    logger.info(f"    -> Saved {len(df_rel)} relationships to '{output_path.name}'")

def generate_relationships(input_dir: Path, scf_rel_dir: Path, framework_rel_dir: Path, config_dir: Path) -> None:
    """
    Orchestrates relationship creation from cleaned CSV files.

    Args:
        input_dir: Directory containing cleaned CSV files.
        scf_rel_dir: Directory to save SCF relationship files.
        framework_rel_dir: Directory to save framework relationship files.
        config_dir: Directory containing the column register configuration.

    Raises:
        RuntimeError: If required files are not found or cannot be processed.
    """
    # Ensure output directories exist
    scf_rel_dir.mkdir(exist_ok=True)
    framework_rel_dir.mkdir(exist_ok=True)

    # Directly construct the path to the controls file, as its name is predictable.
    controls_file: Path = input_dir / SCF_CSV_FILENAME
    if not controls_file.is_file():
        raise RuntimeError(f"Error: Could not find the main controls file at '{controls_file}'. Hint: Ensure the main controls sheet was processed and resulted in '{SCF_CSV_FILENAME}'.")

    # Read all data as strings to preserve formatting (e.g., leading/trailing zeros in IDs).
    df_controls: pd.DataFrame = pd.read_csv(controls_file, low_memory=False, dtype=str, encoding='utf-8')

    column_register_path: Path = config_dir / COLUMN_REGISTER_FILENAME
    if not column_register_path.is_file():
        raise RuntimeError(f"Error: Column register not found at '{column_register_path}'.")

    column_register: pd.DataFrame = pd.read_csv(column_register_path, encoding='utf-8')

    for index, row in column_register.iterrows():
        raw_header: str = row['raw_header']
        label: str = row['label']
        snake_case_header: str = to_snake_case(raw_header)

        if label == 'scf_relationship':
            output_file: Path = scf_rel_dir / f"scf_to_{snake_case_header}.csv"
            create_relationship_file(df_controls, 'scf_id', snake_case_header, snake_case_header, output_file)
        elif label == 'framework_relationship':
            output_file: Path = framework_rel_dir / f"scf_to_{snake_case_header}.csv"
            create_relationship_file(df_controls, 'scf_id', snake_case_header, snake_case_header, output_file)

    # --- Part 3: Create other specific, derived relationships ---

    # 3a. Create Control-to-Domain relationship from SCF.csv
    # This links each control (e.g., GOV-01) to its domain prefix (e.g., GOV).
    df_domain_rel: pd.DataFrame = df_controls[['scf_id']].copy()
    df_domain_rel.dropna(subset=['scf_id'], inplace=True)
    # Domain is the first N characters of the scf_id (configured in constants)
    df_domain_rel['scf_identifier'] = df_domain_rel['scf_id'].str[:DOMAIN_ID_LENGTH]
    domain_output_path: Path = scf_rel_dir / "scf_to_domain.csv"
    df_domain_rel[['scf_id', 'scf_identifier']].to_csv(domain_output_path, index=False, encoding='utf-8')

    # 3b. Create SCF-to-DataPrivacy relationship
    data_privacy_file: Path = input_dir / DATA_PRIVACY_CSV_FILENAME
    if data_privacy_file.is_file():
        df_privacy: pd.DataFrame = pd.read_csv(data_privacy_file, low_memory=False, dtype=str, encoding='utf-8')

        # Check for required columns ('index' and 'secure_controls_framework_scf')
        id_col: str = 'index'
        source_col: str = 'secure_controls_framework_scf'
        if id_col in df_privacy.columns and source_col in df_privacy.columns:
            # This is a "reverse" relationship, so we handle it manually
            # to get the column order (scf_id, data_privacy_id).
            df_rel: pd.DataFrame = df_privacy[[id_col, source_col]].dropna(subset=[source_col]).copy()
            df_rel[source_col] = df_rel[source_col].astype(str).str.split('\n')
            df_rel = df_rel.explode(source_col)
            df_rel[source_col] = df_rel[source_col].str.strip()
            df_rel = df_rel[df_rel[source_col] != '']

            # Swap columns and rename for consistency
            df_rel = df_rel[[source_col, id_col]]
            df_rel.columns = ['scf_id', 'data_privacy_id']
            privacy_output_path: Path = scf_rel_dir / "scf_to_data_privacy.csv"
            df_rel.to_csv(privacy_output_path, index=False, encoding='utf-8')
        else:
            logger.warning(f"Skipping Data Privacy relationship because '{id_col}' or '{source_col}' column not found in '{data_privacy_file.name}'.")
    else:
        logger.info(f"'{data_privacy_file.name}' not found. Skipping Data Privacy relationship processing.")

    logger.info("\nRelationship file generation complete.")

def main() -> None:
    """Parses arguments and calls the main logic."""
    parser = argparse.ArgumentParser(description="Creates relationship mapping files from cleaned CSVs.")
    parser.add_argument("-i", "--input-dir", type=Path, default=Path("csv_cleaned"), help="Directory containing the cleaned CSV files.")
    parser.add_argument("--scf-rel-dir", type=Path, default=Path("scf_relationships"), help="Directory to save SCF-to-entity relationship files.")
    parser.add_argument("--framework-rel-dir", type=Path, default=Path("framework_relationships"), help="Directory to save framework-to-control relationship files.")
    parser.add_argument("-c", "--config-dir", type=Path, default=Path("config"), help="Directory containing the column register.")
    args = parser.parse_args()
    generate_relationships(args.input_dir, args.scf_rel_dir, args.framework_rel_dir, args.config_dir)

if __name__ == "__main__":
    main()