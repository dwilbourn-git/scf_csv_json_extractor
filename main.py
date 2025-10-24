# main.py
# Python-based runner for the Secure Framework Model data pipeline.
# This script replicates the functionality of the Makefile for better cross-platform compatibility.

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Import functions from other scripts
from download_scf import download_scf
from process_scf import split_workbook_to_csv
from clean_csv import clean_csv_files
from create_relationships import generate_relationships
from validate_data import validate_data
from query_version import query_scf_version
from export_json import export_to_json
from export_mongodb import create_mongodb_structure

# Import configuration
from logging_config import setup_logging, get_logger
from constants import (
    DIR_XLSX, DIR_RAW_CSV, DIR_CLEAN_CSV, DIR_SCF_RELATIONSHIPS,
    DIR_FRAMEWORK_RELATIONSHIPS, DIR_JSON_OUTPUT, DIR_CONFIG, SCF_EXCEL_FILENAME,
    SCF_SHA_FILENAME, SCF_VERSION_FILENAME, COLUMN_REGISTER_FILENAME,
    IGNORE_SHEETS
)

# Set up logging
logger = get_logger(__name__)

# --- Configuration ---
PROJECT_ROOT: Path = Path(__file__).parent.resolve()

# Directories
XLSX_DIR: Path = PROJECT_ROOT / DIR_XLSX
RAW_CSV_DIR: Path = PROJECT_ROOT / DIR_RAW_CSV
CLEAN_CSV_DIR: Path = PROJECT_ROOT / DIR_CLEAN_CSV
SCF_REL_DIR: Path = PROJECT_ROOT / DIR_SCF_RELATIONSHIPS
FRAMEWORK_REL_DIR: Path = PROJECT_ROOT / DIR_FRAMEWORK_RELATIONSHIPS
CONFIG_DIR: Path = PROJECT_ROOT / DIR_CONFIG

# Source & Target Files
XLSX_FILE: Path = XLSX_DIR / SCF_EXCEL_FILENAME
SHA_FILE: Path = XLSX_DIR / SCF_SHA_FILENAME
VERSION_FILE: Path = XLSX_DIR / SCF_VERSION_FILENAME
REQUIREMENTS_LOCK: Path = PROJECT_ROOT / "requirements.lock"
COLUMN_REGISTER: Path = CONFIG_DIR / COLUMN_REGISTER_FILENAME

# Stamp files
INSTALL_STAMP: Path = PROJECT_ROOT / ".venv" / ".installed"

# --- Helper Functions ---

def is_up_to_date(target: Path, dependencies: list[Path]) -> bool:
    """Checks if a target file is newer than its dependencies."""
    if not target.exists():
        return False
    target_mtime = target.stat().st_mtime
    for dep in dependencies:
        if not dep.exists() or dep.stat().st_mtime > target_mtime:
            return False
    return True

def touch(path: Path) -> None:
    """Creates a file or updates its modification time."""
    logger.info(f"Touching {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()

# --- Core Logic Functions ---

def do_install() -> None:
    """Installs dependencies if requirements.lock has changed."""
    # Skip installation if running from a PyInstaller bundle (dependencies are already bundled)
    if getattr(sys, 'frozen', False):
        logger.info("Running from bundled executable, skipping dependency installation.")
        return

    if is_up_to_date(INSTALL_STAMP, [REQUIREMENTS_LOCK]):
        logger.info("Environment is up to date.")
        return
    logger.info("Syncing environment with lock file...")
    try:
        subprocess.run(["uv", "pip", "sync", str(REQUIREMENTS_LOCK)], check=True, cwd=PROJECT_ROOT)
        touch(INSTALL_STAMP)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Error installing dependencies: {e}")
        logger.error("Please ensure 'uv' is installed and in your PATH.")
        sys.exit(1)

def do_download(xlsx_dir: Path, sha_file: Path, version_file: Path) -> None:
    """Downloads the SCF file."""
    logger.info("Checking for and downloading latest SCF file...")
    download_scf(xlsx_dir, sha_file, version_file)

def do_process_csv(xlsx_file: Path, sha_file: Path, raw_csv_dir: Path) -> None:
    """Processes the workbook into CSVs."""
    logger.info("Checking for CSV updates and processing workbook...")
    split_workbook_to_csv(xlsx_file, sha_file, raw_csv_dir, IGNORE_SHEETS)

def do_clean_csv() -> None:
    """Cleans the raw CSVs."""
    logger.info("Cleaning raw CSV files...")
    clean_csv_files(RAW_CSV_DIR, CLEAN_CSV_DIR, CONFIG_DIR)

def do_create_relationships() -> None:
    """Creates relationship files."""
    logger.info("Creating relationship mapping files...")
    generate_relationships(CLEAN_CSV_DIR, SCF_REL_DIR, FRAMEWORK_REL_DIR, CONFIG_DIR)

def do_clean() -> None:
    """Removes all generated files and directories."""
    logger.info("Cleaning up generated files and install stamp...")
    # These are the directories that are created by the pipeline
    dirs_to_remove = [
        PROJECT_ROOT / DIR_XLSX,
        PROJECT_ROOT / DIR_RAW_CSV,
        PROJECT_ROOT / DIR_CLEAN_CSV,
        PROJECT_ROOT / DIR_SCF_RELATIONSHIPS,
        PROJECT_ROOT / DIR_FRAMEWORK_RELATIONSHIPS,
        PROJECT_ROOT / DIR_JSON_OUTPUT
    ]
    for d in dirs_to_remove:
        if d.exists():
            logger.info(f"Removing {d}")
            shutil.rmtree(d)
    if INSTALL_STAMP.exists():
        logger.info(f"Removing {INSTALL_STAMP}")
        INSTALL_STAMP.unlink()

def do_show_version() -> None:
    """Queries and displays the current SCF data version."""
    if not VERSION_FILE.exists():
        logger.error("Version file not found. Run the pipeline first.")
        sys.exit(1)
    logger.info("Querying SCF version...")
    query_scf_version(VERSION_FILE)

def do_validate() -> None:
    """Validates the integrity of the generated data."""
    run_pipeline()
    logger.info("Validating data integrity...")
    validate_data(CLEAN_CSV_DIR, SCF_REL_DIR, FRAMEWORK_REL_DIR)

def do_update_register(file_path: Path) -> None:
    """Appends new columns to the column register."""
    if not file_path.is_file():
        logger.error(f"File not found at '{file_path}'.")
        sys.exit(1)

    with open(COLUMN_REGISTER, 'a', encoding='utf-8') as f:
        f.write('\n' + file_path.read_text(encoding='utf-8'))
    logger.info(f"Successfully appended new columns from '{file_path}' to the column register.")

def run_pipeline(output_dir: Optional[Path] = None, config_dir: Optional[Path] = None, output_format: str = "csv", selected_frameworks: Optional[list[str]] = None) -> None:
    """
    Runs the full data pipeline, respecting dependencies.

    Args:
        output_dir: Base directory for output files. Defaults to PROJECT_ROOT.
        config_dir: Directory containing configuration files. Defaults to CONFIG_DIR.
        output_format: Output format - 'csv', 'json', or 'both'. Defaults to 'csv'.
        selected_frameworks: List of framework IDs to include (e.g., ['scf_to_nist_800_53_rev5']). None means all frameworks.
    """
    # If no output directory is specified, use the project default.
    if output_dir is None:
        output_dir = PROJECT_ROOT

    # If no config directory is specified, use the project default.
    if config_dir is None:
        config_dir = CONFIG_DIR

    # Define output paths based on the provided base directory
    xlsx_dir = output_dir / DIR_XLSX
    raw_csv_dir = output_dir / DIR_RAW_CSV
    clean_csv_dir = output_dir / DIR_CLEAN_CSV
    scf_rel_dir = output_dir / DIR_SCF_RELATIONSHIPS
    framework_rel_dir = output_dir / DIR_FRAMEWORK_RELATIONSHIPS

    # Create the directories if they don't exist
    xlsx_dir.mkdir(parents=True, exist_ok=True)
    raw_csv_dir.mkdir(parents=True, exist_ok=True)
    clean_csv_dir.mkdir(parents=True, exist_ok=True)
    scf_rel_dir.mkdir(parents=True, exist_ok=True)
    framework_rel_dir.mkdir(parents=True, exist_ok=True)

    # Define source and target files within the dynamic directories
    xlsx_file = xlsx_dir / SCF_EXCEL_FILENAME
    sha_file = xlsx_dir / SCF_SHA_FILENAME
    version_file = xlsx_dir / SCF_VERSION_FILENAME

    do_install()

    # Validate download step
    do_download(xlsx_dir, sha_file, version_file)
    if not xlsx_file.is_file() or not sha_file.is_file() or not version_file.is_file():
        raise RuntimeError(f"Validation Error: Download step failed. Expected files not found in {xlsx_dir}.")
    logger.info(f"Downloaded files found in {xlsx_dir}.")

    # Validate process_csv step
    do_process_csv(xlsx_file, sha_file, raw_csv_dir)
    if not raw_csv_dir.is_dir() or not any(raw_csv_dir.iterdir()):
        raise RuntimeError(f"Validation Error: CSV processing step failed. No CSV files found in {raw_csv_dir}.")
    logger.info(f"Raw CSV files found in {raw_csv_dir}.")

    # Validate clean_csv step
    clean_csv_files(raw_csv_dir, clean_csv_dir, config_dir)
    if not clean_csv_dir.is_dir() or not any(clean_csv_dir.iterdir()):
        raise RuntimeError(f"Validation Error: CSV cleaning step failed. No cleaned CSV files found in {clean_csv_dir}.")
    logger.info(f"Cleaned CSV files found in {clean_csv_dir}.")

    # Validate create_relationships step
    generate_relationships(clean_csv_dir, scf_rel_dir, framework_rel_dir, config_dir)
    if not scf_rel_dir.is_dir() or not any(scf_rel_dir.iterdir()) or \
       not framework_rel_dir.is_dir() or not any(framework_rel_dir.iterdir()):
        raise RuntimeError(f"Validation Error: Relationship creation step failed. Relationship files not found in {scf_rel_dir} or {framework_rel_dir}.")
    logger.info(f"Relationship files found in {scf_rel_dir} and {framework_rel_dir}.")

    # Export to JSON if requested
    if output_format in ["json", "both"]:
        json_dir = output_dir / DIR_JSON_OUTPUT
        logger.info("\nExporting data to JSON format...")
        export_to_json(clean_csv_dir, json_dir, include_relationships=True,
                      scf_rel_dir=scf_rel_dir, framework_rel_dir=framework_rel_dir,
                      selected_frameworks=selected_frameworks)
        logger.info(f"JSON files found in {json_dir}.")

        # Also create MongoDB-optimized structure
        logger.info("\nCreating MongoDB-optimized structure...")
        mongodb_file = json_dir / "scf_mongodb.json"
        create_mongodb_structure(clean_csv_dir, scf_rel_dir, framework_rel_dir, mongodb_file,
                                selected_frameworks=selected_frameworks)
        logger.info(f"MongoDB-optimized file created: {mongodb_file}")

    logger.info("\nPipeline finished successfully.")

# --- Main Execution ---

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Python-based runner for the Secure Framework Model data pipeline.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="The command to execute")

    # 'run' command
    parser_run = subparsers.add_parser("run", help="Run the full data pipeline (download, process, clean, create relationships).")
    parser_run.add_argument(
        "-o", "--output-dir", type=Path,
        help="Optional: Specify a directory to save the output files."
    )
    parser_run.add_argument(
        "-f", "--format",
        choices=["csv", "json", "both"],
        default="csv",
        help="Output format: 'csv' (default), 'json', or 'both'. JSON output includes all CSV data converted to JSON format."
    )

    # 'install' command
    subparsers.add_parser("install", help="Install/sync Python dependencies using uv.")

    # 'clean' command
    subparsers.add_parser("clean", help="Remove all generated files and directories.")

    # 'version' command
    subparsers.add_parser("version", help="Display the current SCF data version.")

    # 'validate' command
    subparsers.add_parser("validate", help="Run the pipeline and then validate data integrity.")

    # 'update-register' command
    parser_update_register = subparsers.add_parser("update-register", help="Update the column register with new columns.")
    parser_update_register.add_argument(
        "--file",
        type=Path,
        required=True,
        help="Path to the CSV file containing the new columns to add to the register."
    )

    args = parser.parse_args()

    # Initialize logging
    setup_logging(verbose=False)

    if args.command == "run":
        run_pipeline(args.output_dir, output_format=args.format)
    elif args.command == "install":
        do_install()
    elif args.command == "clean":
        do_clean()
    elif args.command == "version":
        do_show_version()
    elif args.command == "validate":
        do_validate()
    elif args.command == "update-register":
        do_update_register(args.file)

if __name__ == "__main__":
    main()