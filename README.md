# Secure Controls Framework - CSV & JSON Extractor

This project is a data pipeline and user-friendly application for processing the Secure Controls Framework (SCF). It downloads the latest SCF data, cleans it, and exports it as normalized CSV files ready for import into any database or data analysis tool.

## Key Features

*   **Automated Data Pipeline:** Robust data pipeline that automates downloading, cleaning, and normalization of SCF data.
*   **Graphical User Interface (GUI):** Simple Tkinter application provides a user-friendly way to run the data pipeline and select output directories.
*   **Framework Selection:** Choose specific frameworks (e.g., NIST, ISO, PCI) or export all 258 available frameworks through the GUI.
*   **Multiple Export Formats:** Export data as CSV, JSON, or both formats with a single click.
*   **MongoDB-Optimized Output:** Generates a denormalized JSON structure optimized for MongoDB with embedded relationships.
*   **Buildable Executable:** Can be bundled into a single executable file using PyInstaller for easy distribution on Windows.
*   **Clean CSV Output:** Generates normalized, database-ready CSV files with standardized column names and clean data.
*   **Relationship Mapping:** Automatically creates relationship tables for many-to-many mappings between controls and frameworks.
*   **Configurable Cleaning:** Data cleaning process is controlled by a `column_register.csv` file, allowing easy customization without modifying source code.
*   **Modern Tooling:** Uses `uv` for fast and reproducible dependency management.

## Getting Started

### Prerequisites

*   Python 3.10+
*   `uv` (Python package installer and manager)

### Setup

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/dwilbourn-git/scf_csv_json_extractor.git
    cd scf_csv_json_extractor
    ```

2.  **Create a virtual environment:**

    ```bash
    uv venv
    ```

3.  **Install dependencies:**

    ```bash
    uv pip sync requirements.lock
    ```

    Or to regenerate the lock file from requirements.txt:

    ```bash
    uv pip compile requirements.txt -o requirements.lock
    uv pip sync requirements.lock
    ```

## Usage

### Running the GUI Application

To run the GUI application, execute the `app.py` script:

```bash
python app.py
```

The GUI will allow you to:
1. Select an output directory for the cleaned data files
2. Choose output format: CSV, JSON, or both
3. Select specific frameworks or export all 258 frameworks
4. Run the full pipeline with a single click
5. View progress and status messages

### Command-Line Interface (CLI)

The project can also be controlled via the command line using the `main.py` script:

*   **Run the full data pipeline:**

    ```bash
    python main.py run
    ```

    This will:
    - Download the latest SCF Excel file from GitHub
    - Split the workbook into individual CSV files
    - Clean and normalize the data
    - Generate relationship mapping files

*   **Run with JSON output:**

    ```bash
    python main.py run --format json
    ```

    Or export both CSV and JSON:

    ```bash
    python main.py run --format both
    ```

*   **Check SCF version:**

    ```bash
    python main.py version
    ```

*   **Validate data integrity:**

    ```bash
    python main.py validate
    ```

    This checks for broken foreign key relationships.

*   **Clean up generated files:**

    ```bash
    python main.py clean
    ```

*   **For a full list of commands:**

    ```bash
    python main.py --help
    ```

### Building the Windows Executable

To build a standalone Windows executable:

```bash
python build.py
```

The executable will be created in the `dist` directory as `Dewis SCF Extractor.exe`.

## Output Structure

When the pipeline runs, it creates the following directory structure:

```
output_directory/
├── scf_full/              # Downloaded Excel file and metadata
├── csv/                   # Raw CSV files split from Excel
├── csv_cleaned/           # Cleaned and normalized CSV files
├── scf_relationships/     # SCF-to-entity relationship mappings
├── framework_relationships/ # Framework-to-control relationship mappings
└── json_output/           # JSON export files (when JSON format selected)
    ├── scf_mongodb.json   # MongoDB-optimized denormalized structure
    └── *.json             # Individual entity JSON files
```

### Main Data Files

- **SCF.csv**: Main controls file with all intrinsic control attributes
- **SCF_Domains_Principles.csv**: Domain and principle definitions
- **Assessment_Objectives.csv**: Assessment objective mappings
- **Risk_Catalog.csv**: Risk definitions
- **Threat_Catalog.csv**: Threat definitions

### Relationship Files

Relationship files use a two-column format for easy database import:
- SCF relationships: Link controls to SCF entities (domains, risks, threats, etc.)
- Framework relationships: Link controls to external frameworks (NIST, ISO, etc.)

### MongoDB JSON Structure

The `scf_mongodb.json` file provides a denormalized, MongoDB-optimized structure where:
- Each control is a complete document with embedded relationships
- Domains, assessment objectives, threats, risks, and evidence requests are embedded directly
- Framework mappings are included as sub-documents
- **Blank fields are omitted** to reduce document size and follow MongoDB best practices
- Ready for direct import with `mongoimport` or MongoDB drivers

Example structure:
```json
{
  "_id": "GOV-01",
  "control_id": "GOV-01",
  "title": "Statutory, Regulatory & Contractual Compliance",
  "domain": {
    "identifier": "GOV",
    "name": "Governance, Risk Management & Compliance"
  },
  "assessment_objectives": [...],
  "threats": [...],
  "framework_mappings": {
    "nist_800_53_rev5": ["PM-1"],
    "iso_iec_27001_2022": ["5.1"]
  }
}
```
### Credits

All credit for the Secure Controls Framework, its content and its relationship mappings goes to the SCF team: https://github.com/securecontrolsframework