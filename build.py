import PyInstaller.__main__
import sys
from pathlib import Path

# --- Configuration ---
PROJECT_ROOT = Path(__file__).parent.resolve()
APP_NAME = "Dewis SCF Extractor"
ENTRY_POINT = "console_wrapper.py"
ICON_FILE = "scf_icon.ico"  # Optional: You can create an icon for your app

# --- Build Logic ---

def main():
    """Runs the PyInstaller build process."""
    build_dir = Path("build")
    dist_dir = Path("dist")

    # Determine the correct path separator for --add-data based on platform
    path_sep = ';' if sys.platform == 'win32' else ':'

    # Arguments for PyInstaller
    args = [
        ENTRY_POINT,
        f"--name={APP_NAME}",
        "--onefile",          # Create a single executable file
        "--console",          # Open a console window for output
        "--collect-all=tkinter", # Ensure all tkinter components are bundled
        f"--add-data={PROJECT_ROOT / 'app.py'}{path_sep}.",
        f"--add-data={PROJECT_ROOT / 'main.py'}{path_sep}.",
        f"--add-data={PROJECT_ROOT / 'logging_config.py'}{path_sep}.",
        f"--add-data={PROJECT_ROOT / 'constants.py'}{path_sep}.",
        f"--add-data={PROJECT_ROOT / 'download_scf.py'}{path_sep}.",
        f"--add-data={PROJECT_ROOT / 'process_scf.py'}{path_sep}.",
        f"--add-data={PROJECT_ROOT / 'clean_csv.py'}{path_sep}.",
        f"--add-data={PROJECT_ROOT / 'create_relationships.py'}{path_sep}.",
        f"--add-data={PROJECT_ROOT / 'validate_data.py'}{path_sep}.",
        f"--add-data={PROJECT_ROOT / 'query_version.py'}{path_sep}.",
        f"--add-data={PROJECT_ROOT / 'export_json.py'}{path_sep}.",
        f"--add-data={PROJECT_ROOT / 'export_mongodb.py'}{path_sep}.",
        "--collect-all=requests", # Explicitly collect the requests library and its dependencies
        "--collect-all=tqdm", # Explicitly collect the tqdm library and its dependencies
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--specpath={build_dir}",
        # Add the config directory as a data file
        f"--add-data={PROJECT_ROOT / 'config'}{path_sep}config",
        # Add the framework_relationships directory
        f"--add-data={PROJECT_ROOT / 'framework_relationships'}{path_sep}framework_relationships"
    ]

    # Add an icon if it exists
    if Path(ICON_FILE).exists():
        args.append(f"--icon={PROJECT_ROOT / ICON_FILE}")

    print(f"==> Running PyInstaller to build '{APP_NAME}'...")
    PyInstaller.__main__.run(args)
    print(f"\nBuild complete. The executable is in the '{dist_dir}' directory.")

if __name__ == "__main__":
    main()
