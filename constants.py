"""
Constants and configuration values for the SCF data pipeline.

This module centralizes all hardcoded values used throughout the pipeline,
making it easier to maintain and modify configuration.
"""

from pathlib import Path

# --- GitHub Repository Configuration ---
GITHUB_REPO = "securecontrolsframework/securecontrolsframework"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/"

# --- Network Configuration ---
GITHUB_API_TIMEOUT = 15  # seconds
DOWNLOAD_TIMEOUT = 60  # seconds
DOWNLOAD_CHUNK_SIZE = 8192  # bytes

# --- Excel Processing Configuration ---
IGNORE_SHEETS = ["Lists"]  # Sheets to skip when processing Excel workbook

# --- CSV Cleaning Configuration ---
# Number of rows to skip when reading specific CSV files
THREAT_CATALOG_SKIP_ROWS = 5
RISK_CATALOG_SKIP_ROWS = 5

# --- File Names ---
SCF_EXCEL_FILENAME = "scf_latest.xlsx"
SCF_SHA_FILENAME = "scf_latest.sha"
SCF_VERSION_FILENAME = "scf_latest.version"
CSV_VERSION_TRACKING = ".version.sha"

SCF_CSV_FILENAME = "SCF.csv"
DOMAINS_CSV_FILENAME = "SCF_Domains_Principles.csv"
ASSESSMENT_OBJECTIVES_CSV_FILENAME = "Assessment_Objectives.csv"
RISK_CATALOG_CSV_FILENAME = "Risk_Catalog.csv"
THREAT_CATALOG_CSV_FILENAME = "Threat_Catalog.csv"
EVIDENCE_REQUEST_LIST_CSV_FILENAME = "Evidence_Request_List.csv"
DATA_PRIVACY_CSV_FILENAME = "Data_Privacy_Mgmt_Principles.csv"

# --- Column Register Configuration ---
COLUMN_REGISTER_FILENAME = "column_register.csv"
ERRATA_COLUMN_PREFIX = "Errata"  # Columns starting with this are ignored in validation

# --- Directory Names ---
DIR_XLSX = "scf_full"
DIR_RAW_CSV = "csv"
DIR_CLEAN_CSV = "csv_cleaned"
DIR_SCF_RELATIONSHIPS = "scf_relationships"
DIR_FRAMEWORK_RELATIONSHIPS = "framework_relationships"
DIR_JSON_OUTPUT = "json_output"
DIR_CONFIG = "config"

# --- App Configuration ---
APP_NAME = "Dewis SCF Extractor"
APP_ICON = "scf_icon.ico"

# --- Domain ID Configuration ---
DOMAIN_ID_LENGTH = 3  # First N characters of scf_id represent the domain

# --- Validation Configuration ---
# Maps foreign key columns to their entity type
RELATIONSHIP_FK_MAP = {
    'scf_id': 'scf',
    'scf_ao_id': 'assessment_objective',
    'data_privacy_id': 'data_privacy',
    'scf_identifier': 'domain',
    'erl_id': 'erl',
    'risk_id': 'risk',
    'threat_id': 'threat',
}

# Maps entity types to their source file and primary key column
ENTITY_CONFIG = {
    'scf': (SCF_CSV_FILENAME, 'scf_id'),
    'assessment_objective': (ASSESSMENT_OBJECTIVES_CSV_FILENAME, 'scf_ao_id'),
    'data_privacy': (DATA_PRIVACY_CSV_FILENAME, 'index'),
    'domain': (DOMAINS_CSV_FILENAME, 'scf_identifier'),
    'erl': ('Evidence_Request_List.csv', 'erl_id'),
    'risk': (RISK_CATALOG_CSV_FILENAME, 'risk_id'),
    'threat': (THREAT_CATALOG_CSV_FILENAME, 'threat_id'),
}
