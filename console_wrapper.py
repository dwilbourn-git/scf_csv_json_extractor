import sys
import traceback
import runpy
from pathlib import Path

def main():
    log_file_path = Path(sys.executable).parent / "error_log.txt"
    original_stderr = sys.stderr

    try:
        # Redirect stderr to a log file
        sys.stderr = open(log_file_path, "w")

        # Run the main application logic from app.py using runpy
        # This is more robust for bundled applications
        runpy.run_module("app", run_name="__main__", alter_sys=True)

    except Exception as e:
        # Print to both original stderr (console) and log file
        original_stderr.write(f"\nFATAL ERROR: An unhandled exception occurred:\n{e}\n")
        traceback.print_exc(file=original_stderr)
        original_stderr.write(f"Full error details saved to {log_file_path}\n")

    finally:
        # Restore original stderr
        if sys.stderr != original_stderr:
            sys.stderr.close()
            sys.stderr = original_stderr

        # Keep the console window open until the user presses Enter
        print("\nPress Enter to Close This Window...")
        input()

if __name__ == "__main__":
    main()
