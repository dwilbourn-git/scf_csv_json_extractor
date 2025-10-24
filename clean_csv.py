#!/usr/bin/env python3
"""
This script cleans the generated CSV files to prepare them for import into a
database (e.g., a graph database). It standardizes headers and cleans data.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

# Import configuration
try:
    from logging_config import get_logger
    from constants import (
        SCF_CSV_FILENAME, DOMAINS_CSV_FILENAME, ASSESSMENT_OBJECTIVES_CSV_FILENAME,
        RISK_CATALOG_CSV_FILENAME, THREAT_CATALOG_CSV_FILENAME,
        COLUMN_REGISTER_FILENAME, ERRATA_COLUMN_PREFIX,
        THREAT_CATALOG_SKIP_ROWS, RISK_CATALOG_SKIP_ROWS
    )
    logger = get_logger(__name__)
except ImportError:
    # Fallback for standalone usage
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    SCF_CSV_FILENAME = "SCF.csv"
    DOMAINS_CSV_FILENAME = "SCF_Domains_Principles.csv"
    ASSESSMENT_OBJECTIVES_CSV_FILENAME = "Assessment_Objectives.csv"
    RISK_CATALOG_CSV_FILENAME = "Risk_Catalog.csv"
    THREAT_CATALOG_CSV_FILENAME = "Threat_Catalog.csv"
    COLUMN_REGISTER_FILENAME = "column_register.csv"
    ERRATA_COLUMN_PREFIX = "Errata"
    THREAT_CATALOG_SKIP_ROWS = 5
    RISK_CATALOG_SKIP_ROWS = 5

def to_snake_case(name: str) -> str:
    """
    Converts a string to a database-friendly snake_case format.
    Example: "SCF #" -> "scf_id", "NIST 800-53 R5" -> "nist_800_53_r5"
    """
    name = name.strip()
    # Add specific overrides for known problematic headers first
    if name == '#':
        return 'index'
    if name == 'SCF #':
        return 'scf_id'
    # Add an explicit override for "SCF Control" to ensure consistency
    if name == 'SCF Control':
        return 'scf_control'

    if name.endswith(' #'):
        # Handles "Threat #", etc. -> "threat_id"
        name = name[:-2] + '_id'

    # A simpler, more robust snake_casing for remaining headers
    # Lowercase, then replace all non-alphanumeric sequences with a single underscore.
    s1 = name.lower()
    s2 = re.sub(r'[^a-z0-9]+', '_', s1)
    return s2.strip('_')

def remove_invisible_chars(data):
    """
    Removes invisible and control characters from a string, while preserving
    common whitespace. Handles non-string data by returning it as is.
    """
    if isinstance(data, str):
        # This regex removes control characters but keeps space, tab, newline, etc.
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', data).strip()
    return data

def convert_to_boolean(value):
    """Converts 'x', 'true', 'yes', '1' to True and other values to False."""
    if isinstance(value, str):
        val_lower = value.strip().lower()
        if val_lower in ['x', 'true', 'yes', '1']:
            return True
    return False

def clean_generic_csv(file_path: Path) -> pd.DataFrame:
    """Applies generic cleaning rules (header standardization) to a CSV."""
    print(f"  - Applying generic header cleaning to '{file_path.name}'.")
    # Read all data as strings to preserve formatting (e.g., leading/trailing zeros).
    df = pd.read_csv(file_path, low_memory=False, dtype=str)
    df.columns = [to_snake_case(col) for col in df.columns]
    return df

def clean_scf_controls(file_path: Path, column_register: pd.DataFrame) -> pd.DataFrame:
    """
    Applies specific, advanced cleaning rules to the main SCF.csv file.
    """
    print("  - Applying 'SCF Controls' specific cleaning rules.")
    # Read all data as strings to preserve formatting.
    df = pd.read_csv(file_path, low_memory=False, dtype=str)

    # 1. Remove columns marked for removal in the column register.
    columns_to_remove = column_register[column_register['label'] == 'remove']['raw_header'].tolist()
    df.drop(columns=columns_to_remove, inplace=True, errors='ignore')
    print(f"    - Dropping {len(columns_to_remove)} columns marked for removal.")

    # 2. Standardize all remaining column headers to snake_case.
    df.columns = [to_snake_case(col) for col in df.columns]

    # 3. Identify and convert columns that only contain 'x' and blank values to boolean.
    print("    - Scanning for and converting boolean-like columns (x/blank)...")
    converted_count = 0
    for col in df.columns:
        # Get a set of unique, non-null values, converted to lowercase strings.
        unique_vals = set(str(v).lower() for v in df[col].dropna().unique())
        # If the set of unique values is empty or is exactly {'x'}, it's a boolean-like column.
        if not unique_vals or unique_vals.issubset({'x', ''}):
            df[col] = df[col].apply(convert_to_boolean)
            converted_count += 1
    if converted_count > 0:
        print(f"    - Converted {converted_count} columns to boolean.")
    return df

def clean_scf_domains_principles(file_path: Path) -> pd.DataFrame:
    """
    Applies cleaning rules to the SCF_Domains_Principles.csv file.
    This includes header cleaning and removing invisible characters from data.
    """
    print(f"  - Applying 'SCF Domains & Principles' cleaning rules.")
    df = pd.read_csv(file_path, low_memory=False, dtype=str)  # Read all as strings to preserve formatting

    # 1. Rename the '#' column to 'index' for ordering.
    try:
        original_id_col = next(col for col in df.columns if col.strip() == '#')
        df.rename(columns={original_id_col: 'index'}, inplace=True)
        print(f"    - Renamed original column '{original_id_col}' to 'index'.")
    except StopIteration:
        print(f"  - Warning: Could not find the '#' column in '{file_path.name}'. Skipping rename.", file=sys.stderr)

    # 2. Clean the rest of the headers using the standard snake_case function.
    rename_map = {col: to_snake_case(col) for col in df.columns if col != 'index'}
    df.rename(columns=rename_map, inplace=True)

    # 3. Remove invisible characters from all data cells.
    print("    - Removing invisible characters from data fields.")
    for col in df.columns:
        df[col] = df[col].map(remove_invisible_chars)

    # 4. Drop any rows where the primary key 'scf_identifier' is missing.
    print("    - Dropping rows with no scf_identifier.")
    df.dropna(subset=['scf_identifier'], inplace=True)
    df = df[df['scf_identifier'].str.strip() != '']
    return df.reset_index(drop=True)

def clean_threat_catalog(file_path: Path) -> pd.DataFrame:
    """
    Applies cleaning rules to the Threat_Catalog CSV. This involves removing
    junk header/footer rows and selecting/renaming specific columns.

    Args:
        file_path: Path to the Threat_Catalog.csv file.

    Returns:
        Cleaned DataFrame with standardized columns.
    """
    logger.info("  - Applying 'Threat Catalog' cleaning rules.")
    # 1. Read the CSV, skipping the initial N junk rows and using the next row as the header.
    df = pd.read_csv(file_path, skiprows=THREAT_CATALOG_SKIP_ROWS, header=0, dtype=str, encoding='utf-8')

    # 2. Define the columns to keep and their new, standardized names.
    columns_to_keep = {
        "Threat Grouping": "threat_grouping",
        "Threat #": "threat_id",
        "Threat*": "threat",
        "Threat Description": "threat_description"
    }

    # 3. Filter for only the columns we need and rename them.
    df_renamed = df[list(columns_to_keep.keys())].rename(columns=columns_to_keep)

    # 4. Fill the threat_grouping column based on the threat_id. This ensures
    #    that every row has the correct grouping, instead of just the first row.
    df_renamed['threat_grouping'] = np.where(
        df_renamed['threat_id'].str.contains('NT', na=False),
        'Natural Threat',
        'Man-Made Threat'
    )

    # 5. Drop rows where 'threat_id' is null, which removes footers and empty lines.
    return df_renamed.dropna(subset=['threat_id']).reset_index(drop=True)

def clean_risk_catalog(file_path: Path) -> pd.DataFrame:
    """
    Applies cleaning rules to the Risk_Catalog CSV. This involves removing junk
    header/footer rows, selecting/renaming specific columns, and filling in
    grouping data.

    Args:
        file_path: Path to the Risk_Catalog.csv file.

    Returns:
        Cleaned DataFrame with standardized columns.
    """
    logger.info("  - Applying 'Risk Catalog' cleaning rules.")
    # 1. Read the CSV, skipping the initial N junk rows. The next row becomes the header.
    df = pd.read_csv(file_path, skiprows=RISK_CATALOG_SKIP_ROWS, header=0, dtype=str, encoding='utf-8')

    # 2. The first row of data is also junk text; drop it and reset the index.
    df = df.drop(index=0).reset_index(drop=True)

    # 3. Dynamically find the full names of the columns we need to keep, as they
    #    contain newlines and are not stable.
    try:
        risk_col_name = next(col for col in df.columns if col.startswith('Risk*'))
        desc_col_name = next(col for col in df.columns if col.startswith('Description'))
        nist_col_name = next(col for col in df.columns if col.startswith('NIST CSF'))
    except StopIteration:
        logger.error(f"Could not find expected columns in '{file_path.name}'. Skipping file.")
        return pd.DataFrame() # Return empty DataFrame on error

    # 4. Define the columns to keep and their new, standardized names.
    columns_to_keep = {
        "Risk Grouping": "risk_grouping",
        "Risk #": "risk_id",
        risk_col_name: "risk",
        desc_col_name: "risk_description",
        nist_col_name: "nist_csf_function"
    }

    # 5. Filter for only the columns we need and rename them.
    df_renamed = df[list(columns_to_keep.keys())].rename(columns=columns_to_keep)

    # 6. Forward-fill the risk_grouping column to propagate the group name to all its members.
    df_renamed['risk_grouping'] = df_renamed['risk_grouping'].ffill()

    # 7. Drop rows where 'risk_id' is null, which removes footers and empty lines.
    return df_renamed.dropna(subset=['risk_id']).reset_index(drop=True)

def clean_assessment_objectives(file_path: Path) -> pd.DataFrame:
    """
    Applies cleaning rules to the Assessment_Objectives CSV. This involves
    selecting specific columns and standardizing their headers.

    Args:
        file_path: Path to the Assessment_Objectives.csv file.

    Returns:
        Cleaned DataFrame with standardized columns.
    """
    logger.info("  - Applying 'Assessment Objectives' cleaning rules.")
    df = pd.read_csv(file_path, low_memory=False, dtype=str, encoding='utf-8')

    # Dynamically find the full names of the columns we need to keep, as some
    # contain newlines and are not stable.
    try:
        ao_desc_col = next(col for col in df.columns if col.startswith('SCF Assessment Objective (AO)'))
        baseline_col = next(col for col in df.columns if col.startswith('SCF Baseline'))
        dhs_col = next(col for col in df.columns if col.startswith('DHS ZTCF'))
    except StopIteration:
        logger.error(f"Could not find expected columns in '{file_path.name}'. Skipping file.")
        return pd.DataFrame()

    # 1. Define the exact columns to keep.
    columns_to_keep = [
        "SCF #", "SCF AO #", ao_desc_col, "SCF Assessment Objective (AO) Origin(s)",
        "Notes / Errata", baseline_col, dhs_col, "NIST 800-53 R5 AOs",
        "NIST 800-171 R2 AOs", "NIST 800-171 R3 AOs", "NIST 800-172 AOs"
    ]

    # 2. Filter the DataFrame to only the desired columns.
    df_filtered = df[columns_to_keep].copy()

    # 3. Rename the columns according to the specified rules.
    new_headers = {col: to_snake_case(col) for col in df_filtered.columns}
    new_headers[ao_desc_col] = "scf_assessment_objective" # Apply special renaming rule
    df_filtered.rename(columns=new_headers, inplace=True)

    # 4. Convert mapping columns from 'x'/blank to boolean True/False.
    boolean_cols: list[str] = [
        'scf_baseline_a_os',
        'dhs_ztcf_a_os',
        'nist_800_53_r5_a_os',
        'nist_800_171_r2_a_os',
        'nist_800_171_r3_a_os',
        'nist_800_172_a_os'
    ]

    logger.info("  - Converting mapping columns to boolean (True/False).")
    for col in boolean_cols:
        if col in df_filtered.columns:
            df_filtered[col] = df_filtered[col].apply(convert_to_boolean)

    # 5. Drop rows where the primary key 'scf_ao_id' is missing.
    logger.info("  - Dropping rows with no scf_ao_id.")
    df_filtered.dropna(subset=['scf_ao_id'], inplace=True)
    df_filtered = df_filtered[df_filtered['scf_ao_id'].str.strip() != '']

    return df_filtered.reset_index(drop=True)

def get_cleaning_function(filename: str) -> Optional[Callable]:
    """
    Returns the appropriate cleaning function based on the filename.
    This acts as a router to dispatch files to the correct logic.

    Args:
        filename: Name of the CSV file to be cleaned.

    Returns:
        The appropriate cleaning function, or clean_generic_csv for unknown files.
    """
    name_lower: str = filename.lower()
    # The main controls file has specific, complex cleaning rules.
    if name_lower == SCF_CSV_FILENAME.lower():
        return clean_scf_controls
    if DOMAINS_CSV_FILENAME.lower().replace('.csv', '') in name_lower:
        return clean_scf_domains_principles
    if ASSESSMENT_OBJECTIVES_CSV_FILENAME.lower().replace('.csv', '').replace('_', '') in name_lower.replace('_', ''):
        return clean_assessment_objectives
    if "risk" in name_lower:
        return clean_risk_catalog
    if "threat" in name_lower:
        return clean_threat_catalog

    # For all other files, apply a generic header cleaning.
    return clean_generic_csv

def clean_csv_files(input_dir: Path, output_dir: Path, config_dir: Path) -> None:
    """
    Orchestrates the cleaning process for all known CSV files.

    Args:
        input_dir: Directory containing raw CSV files.
        output_dir: Directory to save cleaned CSV files.
        config_dir: Directory containing the column register configuration.

    Raises:
        RuntimeError: If input directory doesn't exist, column register not found,
                     or new unregistered columns are detected.
    """
    if not input_dir.is_dir():
        raise RuntimeError(f"Error: Input directory '{input_dir}' not found. Hint: Run 'make process' first to generate the raw CSVs.")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Validate the column register
    scf_raw_path: Path = input_dir / SCF_CSV_FILENAME
    column_register_path: Path = config_dir / COLUMN_REGISTER_FILENAME
    if not column_register_path.is_file():
        raise RuntimeError(f"Error: Column register not found at '{column_register_path}'.")

    column_register: pd.DataFrame = pd.read_csv(column_register_path, encoding='utf-8')
    registered_columns: set[str] = set(column_register['raw_header'])
    raw_scf_columns: set[str] = set(pd.read_csv(scf_raw_path, nrows=0, encoding='utf-8').columns)

    new_columns: set[str] = raw_scf_columns - registered_columns
    # Filter out columns that start with 'Errata' as they are expected to change
    new_columns = {col for col in new_columns if not col.startswith(ERRATA_COLUMN_PREFIX)}

    removed_columns: set[str] = registered_columns - raw_scf_columns

    if new_columns:
        raise RuntimeError("Error: New, unregistered columns found in SCF.csv: " + ", ".join(new_columns) + ". Please update the column_register.csv file.")

    if removed_columns:
        logger.info("Info: Columns removed from SCF.csv:")
        for col in removed_columns:
            logger.info(f"  - {col}")

    all_raw_csvs: list[Path] = list(input_dir.glob("*.csv"))
    if not all_raw_csvs:
        logger.warning(f"No raw CSV files found in '{input_dir}' to clean.")
        return

    cleaned_count: int = 0
    for file_path in tqdm(all_raw_csvs, desc="Cleaning CSVs", unit="file"):
        clean_func = get_cleaning_function(file_path.name)

        if clean_func:
            if file_path.name == SCF_CSV_FILENAME:
                df_cleaned = clean_func(file_path, column_register)
            else:
                df_cleaned = clean_func(file_path)

            if not df_cleaned.empty:
                output_path: Path = output_dir / file_path.name
                df_cleaned.to_csv(output_path, index=False, encoding='utf-8')
                cleaned_count += 1

    if cleaned_count > 0:
        logger.info(f"\nSuccessfully cleaned {cleaned_count} file(s). Output is in '{output_dir}'")
    else:
        logger.info("\n- No files with specific cleaning rules were found. Nothing to do.")

def main() -> None:
    """Parses command-line arguments and initiates the cleaning process."""
    parser = argparse.ArgumentParser(
        description="Cleans raw CSV files for database import.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i", "--input-dir", type=Path, default=Path("csv"),
        help="Directory containing the raw CSV files to clean."
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=Path("csv_cleaned"),
        help="Directory to save the cleaned CSV files."
    )
    parser.add_argument(
        "-c", "--config-dir", type=Path, default=Path("config"),
        help="Directory containing the column register."
    )
    args = parser.parse_args()

    clean_csv_files(args.input_dir, args.output_dir, args.config_dir)

if __name__ == "__main__":
    main()