import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import sys
import os
import importlib.util
import importlib.machinery
import logging

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent.resolve()
    return base_path / relative_path

sys.path.append(str(get_resource_path('.')))

# Dynamically load main.py as a module
main_path = get_resource_path('main.py')
if not main_path.is_file():
    raise RuntimeError(f"Error: main.py not found at {main_path}")

loader = importlib.machinery.SourceFileLoader('pipeline', str(main_path))
spec = importlib.util.spec_from_loader(loader.name, loader)
pipeline = importlib.util.module_from_spec(spec)
loader.exec_module(pipeline)

# Import logging configuration
logging_config_path = get_resource_path('logging_config.py')
if logging_config_path.is_file():
    logging_loader = importlib.machinery.SourceFileLoader('logging_config', str(logging_config_path))
    logging_spec = importlib.util.spec_from_loader(logging_loader.name, logging_loader)
    logging_config = importlib.util.module_from_spec(logging_spec)
    logging_loader.exec_module(logging_config)
    # Set up logging for the GUI app
    logging_config.setup_logging(verbose=False)

class SCFExtractorApp:
    def __init__(self, master):
        self.master = master
        master.title("Dewi's SCF Extractor")
        master.geometry("750x750")
        master.resizable(True, True)

        # Welcome Message
        self.welcome_label = tk.Label(
            master,
            text="Thanks for downloading Dewi's SCF Extractor!\n\nPlease select a directory for your extracted SCF files",
            wraplength=450,
            justify="left",
            font=("Arial", 10)
        )
        self.welcome_label.pack(pady=20)

        # Folder Selection
        self.path_frame = tk.Frame(master)
        self.path_frame.pack(pady=10)

        self.path_entry = tk.Entry(self.path_frame, width=50)
        self.path_entry.pack(side=tk.LEFT, padx=5)
        self.path_entry.bind("<KeyRelease>", self.validate_path)

        self.browse_button = tk.Button(self.path_frame, text="Browse", command=self.select_folder)
        self.browse_button.pack(side=tk.LEFT, padx=5)

        # Output Format Selection
        self.format_frame = tk.Frame(master)
        self.format_frame.pack(pady=15)

        self.format_label = tk.Label(self.format_frame, text="Output Format:", font=("Arial", 10, "bold"))
        self.format_label.pack(anchor=tk.W, padx=20)

        self.format_var = tk.StringVar(value="csv")

        self.format_options_frame = tk.Frame(self.format_frame)
        self.format_options_frame.pack(anchor=tk.W, padx=40, pady=5)

        self.csv_radio = tk.Radiobutton(
            self.format_options_frame,
            text="CSV only (comma-separated values)",
            variable=self.format_var,
            value="csv",
            font=("Arial", 9)
        )
        self.csv_radio.pack(anchor=tk.W)

        self.json_radio = tk.Radiobutton(
            self.format_options_frame,
            text="JSON only (JavaScript Object Notation)",
            variable=self.format_var,
            value="json",
            font=("Arial", 9)
        )
        self.json_radio.pack(anchor=tk.W)

        self.both_radio = tk.Radiobutton(
            self.format_options_frame,
            text="Both CSV and JSON",
            variable=self.format_var,
            value="both",
            font=("Arial", 9)
        )
        self.both_radio.pack(anchor=tk.W)

        # Framework Selection
        self.framework_frame = tk.Frame(master)
        self.framework_frame.pack(pady=10, fill=tk.BOTH, expand=True)

        self.framework_label = tk.Label(self.framework_frame, text="Framework Selection (optional - leave empty for all):", font=("Arial", 10, "bold"))
        self.framework_label.pack(anchor=tk.W, padx=20)

        # Load available frameworks (now categorized)
        self.categorized_frameworks = self.load_available_frameworks()
        self.total_frameworks = sum(len(frameworks) for frameworks in self.categorized_frameworks.values())

        # Framework selection controls
        self.framework_controls_frame = tk.Frame(self.framework_frame)
        self.framework_controls_frame.pack(anchor=tk.W, padx=40, pady=5)

        self.select_all_button = tk.Button(self.framework_controls_frame, text="Select All", command=self.select_all_frameworks, font=("Arial", 8))
        self.select_all_button.pack(side=tk.LEFT, padx=2)

        self.deselect_all_button = tk.Button(self.framework_controls_frame, text="Deselect All", command=self.deselect_all_frameworks, font=("Arial", 8))
        self.deselect_all_button.pack(side=tk.LEFT, padx=2)

        self.expand_all_button = tk.Button(self.framework_controls_frame, text="Expand All", command=self.expand_all_categories, font=("Arial", 8))
        self.expand_all_button.pack(side=tk.LEFT, padx=2)

        self.collapse_all_button = tk.Button(self.framework_controls_frame, text="Collapse All", command=self.collapse_all_categories, font=("Arial", 8))
        self.collapse_all_button.pack(side=tk.LEFT, padx=2)

        self.framework_count_label = tk.Label(self.framework_controls_frame, text=f"0 of {self.total_frameworks} selected", font=("Arial", 8))
        self.framework_count_label.pack(side=tk.LEFT, padx=10)

        # Scrollable framework tree
        self.framework_tree_frame = tk.Frame(self.framework_frame)
        self.framework_tree_frame.pack(anchor=tk.W, padx=40, pady=5, fill=tk.BOTH, expand=True)

        self.framework_tree_scrollbar = tk.Scrollbar(self.framework_tree_frame, orient="vertical")
        self.framework_tree = ttk.Treeview(self.framework_tree_frame, yscrollcommand=self.framework_tree_scrollbar.set, height=10)
        self.framework_tree_scrollbar.config(command=self.framework_tree.yview)

        self.framework_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.framework_tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure tree columns
        self.framework_tree["columns"] = ("count",)
        self.framework_tree.column("#0", width=400, minwidth=200)
        self.framework_tree.column("count", width=80, minwidth=50, anchor=tk.E)
        self.framework_tree.heading("#0", text="Framework / Category")
        self.framework_tree.heading("count", text="Count")

        # Populate tree with categorized frameworks
        self.framework_items = {}  # Map framework_id to tree item
        for category in sorted(self.categorized_frameworks.keys()):
            frameworks = self.categorized_frameworks[category]
            # Add category node
            category_node = self.framework_tree.insert("", "end", text=f"☐ {category}", values=(f"{len(frameworks)}",), tags=("category",))

            # Add framework children
            for framework_id, framework_name in frameworks:
                item_id = self.framework_tree.insert(category_node, "end", text=f"☐ {framework_name}", values=("",), tags=("framework",))
                self.framework_items[framework_id] = {"tree_id": item_id, "category": category_node, "selected": False}

        # Bind click events for checkboxes
        self.framework_tree.tag_bind("category", "<Button-1>", self.toggle_category)
        self.framework_tree.tag_bind("framework", "<Button-1>", self.toggle_framework)

        # Buttons
        self.button_frame = tk.Frame(master)
        self.button_frame.pack(pady=15)

        self.cancel_button = tk.Button(self.button_frame, text="Cancel", command=master.quit)
        self.cancel_button.pack(side=tk.RIGHT, padx=5)

        self.next_button = tk.Button(self.button_frame, text="Next", command=self.start_extraction, state=tk.DISABLED)
        self.next_button.pack(side=tk.RIGHT, padx=5)

        self.output_path = None

    def select_folder(self):
        folder_selected = filedialog.askdirectory(title="Select a folder to save the cleaned SCF data")
        if folder_selected:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder_selected)
            self.output_path = Path(folder_selected) / "clean_scf_csv"
            self.validate_path()

    def validate_path(self, event=None):
        current_path = self.path_entry.get()
        if current_path and Path(current_path).is_dir():
            self.next_button.config(state=tk.NORMAL)
            self.output_path = Path(current_path) / "clean_scf_csv"
        else:
            self.next_button.config(state=tk.DISABLED)
            self.output_path = None

    def categorize_framework(self, name):
        """Categorize a framework based on its name."""
        if name.startswith('americas_'):
            return 'Americas'
        elif name.startswith('apac_'):
            return 'Asia Pacific (APAC)'
        elif name.startswith('emea_'):
            return 'Europe, Middle East & Africa (EMEA)'
        elif name.startswith('us_'):
            state_codes = ['_ak_', '_ca_', '_co_', '_il_', '_ma_', '_nv_', '_ny_', '_or_', '_tn_', '_tx_', '_va_', '_vt_']
            if any(state in name for state in state_codes):
                return 'United States - State Laws'
            else:
                return 'United States - Federal'
        elif name.startswith('nist_'):
            return 'NIST Standards'
        elif name.startswith('iso_'):
            return 'ISO Standards'
        elif name.startswith('pci'):
            return 'Payment Card Industry (PCI)'
        elif name.startswith('cis_'):
            return 'CIS Controls'
        elif name.startswith('aicpa_'):
            return 'Accounting & Audit Standards'
        elif name.startswith('iec_'):
            return 'IEC Standards'
        elif name.startswith('owasp_'):
            return 'OWASP'
        elif name.startswith('mitre_'):
            return 'MITRE'
        elif name.startswith('shared_') or name in ['cobit_2019', 'coso_v2017', 'csa_ccm_v4', 'csa_iot_scf_v2']:
            return 'Industry Standards'
        else:
            return 'International Standards'

    def load_available_frameworks(self):
        """Load and categorize frameworks from framework_relationships directory."""
        try:
            # Try to get the framework_relationships directory from bundled resources first
            framework_dir = get_resource_path('framework_relationships')
            if not framework_dir.exists():
                # Fallback to the development location
                framework_dir = Path(__file__).parent / 'framework_relationships'

            if framework_dir.exists():
                categorized = {}
                for file in framework_dir.glob('scf_to_*.csv'):
                    framework_id = file.stem  # Keep full ID: scf_to_xxx
                    framework_name = framework_id.replace('scf_to_', '').replace('_', ' ').title()
                    category = self.categorize_framework(framework_id.replace('scf_to_', ''))

                    if category not in categorized:
                        categorized[category] = []
                    categorized[category].append((framework_id, framework_name))

                # Sort categories and frameworks within each category
                for category in categorized:
                    categorized[category].sort(key=lambda x: x[1])

                return categorized
            return {}
        except Exception as e:
            print(f"Warning: Could not load frameworks: {e}")
            return {}

    def toggle_framework(self, event):
        """Toggle a framework's selection state."""
        item = self.framework_tree.focus()
        if item:
            # Find framework by tree_id
            framework_id = None
            for fid, fdata in self.framework_items.items():
                if fdata["tree_id"] == item:
                    framework_id = fid
                    break

            if framework_id:
                # Toggle selection
                self.framework_items[framework_id]["selected"] = not self.framework_items[framework_id]["selected"]
                selected = self.framework_items[framework_id]["selected"]

                # Update checkbox symbol
                current_text = self.framework_tree.item(item, "text")
                new_text = current_text.replace("☐", "☑" if selected else "☐").replace("☑", "☑" if selected else "☐")
                if not selected and "☑" in current_text:
                    new_text = current_text.replace("☑", "☐")
                elif selected and "☐" in current_text:
                    new_text = current_text.replace("☐", "☑")
                self.framework_tree.item(item, text=new_text)

                # Update category checkbox
                self.update_category_checkbox(self.framework_items[framework_id]["category"])
                self.update_framework_count()

    def toggle_category(self, event):
        """Toggle all frameworks in a category."""
        item = self.framework_tree.focus()
        if item:
            # Get all children (frameworks) in this category
            children = self.framework_tree.get_children(item)
            if not children:
                return

            # Determine if we're selecting or deselecting (based on current state)
            current_text = self.framework_tree.item(item, "text")
            select_all = "☐" in current_text

            # Toggle all children
            for child in children:
                for fid, fdata in self.framework_items.items():
                    if fdata["tree_id"] == child:
                        self.framework_items[fid]["selected"] = select_all
                        child_text = self.framework_tree.item(child, "text")
                        new_text = child_text.replace("☐", "☑" if select_all else "☐").replace("☑", "☑" if select_all else "☐")
                        if not select_all:
                            new_text = child_text.replace("☑", "☐")
                        else:
                            new_text = child_text.replace("☐", "☑")
                        self.framework_tree.item(child, text=new_text)

            # Update category checkbox
            new_category_text = current_text.replace("☐", "☑" if select_all else "☐").replace("☑", "☑" if select_all else "☐")
            if not select_all:
                new_category_text = current_text.replace("☑", "☐")
            else:
                new_category_text = current_text.replace("☐", "☑")
            self.framework_tree.item(item, text=new_category_text)

            self.update_framework_count()

    def update_category_checkbox(self, category_item):
        """Update a category's checkbox based on its children's state."""
        children = self.framework_tree.get_children(category_item)
        selected_count = sum(1 for child in children
                           for fid, fdata in self.framework_items.items()
                           if fdata["tree_id"] == child and fdata["selected"])

        current_text = self.framework_tree.item(category_item, "text")
        if selected_count == 0:
            new_text = current_text.replace("☑", "☐")
        elif selected_count == len(children):
            new_text = current_text.replace("☐", "☑")
        else:
            new_text = current_text.replace("☑", "☐").replace("☐", "☑", 1)  # Partial selection

        self.framework_tree.item(category_item, text=new_text)

    def select_all_frameworks(self):
        """Select all frameworks."""
        for fid in self.framework_items:
            self.framework_items[fid]["selected"] = True
            item_text = self.framework_tree.item(self.framework_items[fid]["tree_id"], "text")
            self.framework_tree.item(self.framework_items[fid]["tree_id"], text=item_text.replace("☐", "☑"))

        # Update all category checkboxes
        for category_item in self.framework_tree.get_children():
            cat_text = self.framework_tree.item(category_item, "text")
            self.framework_tree.item(category_item, text=cat_text.replace("☐", "☑"))

        self.update_framework_count()

    def deselect_all_frameworks(self):
        """Deselect all frameworks."""
        for fid in self.framework_items:
            self.framework_items[fid]["selected"] = False
            item_text = self.framework_tree.item(self.framework_items[fid]["tree_id"], "text")
            self.framework_tree.item(self.framework_items[fid]["tree_id"], text=item_text.replace("☑", "☐"))

        # Update all category checkboxes
        for category_item in self.framework_tree.get_children():
            cat_text = self.framework_tree.item(category_item, "text")
            self.framework_tree.item(category_item, text=cat_text.replace("☑", "☐"))

        self.update_framework_count()

    def expand_all_categories(self):
        """Expand all category nodes."""
        for category_item in self.framework_tree.get_children():
            self.framework_tree.item(category_item, open=True)

    def collapse_all_categories(self):
        """Collapse all category nodes."""
        for category_item in self.framework_tree.get_children():
            self.framework_tree.item(category_item, open=False)

    def update_framework_count(self):
        """Update the framework selection count label."""
        selected_count = sum(1 for fdata in self.framework_items.values() if fdata["selected"])
        self.framework_count_label.config(text=f"{selected_count} of {self.total_frameworks} selected")

    def get_selected_frameworks(self):
        """Get list of selected framework IDs."""
        selected = [fid for fid, fdata in self.framework_items.items() if fdata["selected"]]
        return selected if selected else None  # None means "all frameworks"

    def start_extraction(self):
        if not self.output_path:
            messagebox.showerror("Error", "Please select a valid output directory.")
            return

        # Get selected format
        output_format = self.format_var.get()

        # Get selected frameworks
        selected_frameworks = self.get_selected_frameworks()

        # Destroy the GUI window to show console output
        self.master.destroy()

        print("\nStarting SCF data extraction...")
        print(f"Output will be saved to: {self.output_path}")
        print(f"Output format: {output_format.upper()}")
        if selected_frameworks:
            print(f"Selected frameworks: {len(selected_frameworks)} of 258")
        else:
            print("Selected frameworks: All (258)")

        try:
            # Ensure the main output directory exists
            self.output_path.mkdir(parents=True, exist_ok=True)

            # For the app, we need to resolve the path to the config directory
            config_dir = get_resource_path('config')

            # Run the pipeline steps, directing output to the selected folder
            pipeline.run_pipeline(self.output_path, config_dir, output_format=output_format, selected_frameworks=selected_frameworks)

            format_msg = {
                "csv": "CSV files",
                "json": "JSON files",
                "both": "CSV and JSON files"
            }

            messagebox.showinfo("Success", f"Extraction Complete!\n\nThe cleaned SCF data ({format_msg[output_format]}) has been saved to:\n{self.output_path}")
            self.pause_console()

        except Exception as e:
            print(f"\nERROR: An unexpected error occurred during extraction: {e}", file=sys.stderr)
            messagebox.showerror("Error", f"An error occurred during extraction. Please check the console for details.\n\nError: {e}")
            self.pause_console()

    def pause_console(self):
        input("\nPress Enter to Close This Window...")


if __name__ == "__main__":
    root = tk.Tk()
    app = SCFExtractorApp(root)
    root.mainloop()
    # Ensure console stays open after GUI closes, in case of errors not caught by try/except
    if sys.stdin and sys.stdin.isatty(): # Check if running in a real console
        input("\nPress Enter to Close This Window...")