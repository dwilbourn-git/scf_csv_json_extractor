# GUI Format Selection Feature

## Overview
Added output format selection to the GUI executable (Dewi's SCF Extractor), allowing users to choose between CSV, JSON, or both formats.

## User Interface Changes

### Previous UI
- Simple folder selection
- Only CSV output

### New UI (500x350 pixels)
- Folder selection
- **Format selection radio buttons:**
  - ⚪ CSV only (comma-separated values) - **DEFAULT**
  - ⚪ JSON only (JavaScript Object Notation)
  - ⚪ Both CSV and JSON

## How It Works

1. User launches `Dewis SCF Extractor.exe`
2. Selects output directory
3. Chooses desired format (CSV/JSON/Both)
4. Clicks "Next"
5. Pipeline runs with selected format
6. Success message shows which format(s) were generated

## Output Examples

### CSV Only (Default)
```
output_directory/
├── csv_cleaned/
│   ├── SCF.csv
│   ├── SCF_Domains_Principles.csv
│   └── ...
├── scf_relationships/
│   ├── scf_to_domain.csv
│   └── ...
└── framework_relationships/
    ├── scf_to_nist_800_53_rev5.csv
    └── ...
```

### JSON Only
```
output_directory/
└── json_output/
    ├── SCF.json
    ├── SCF_Domains_Principles.json
    ├── scf_relationships/
    │   ├── scf_to_domain.json
    │   └── ...
    └── framework_relationships/
        ├── scf_to_nist_800_53_rev5.json
        └── ...
```

### Both
```
output_directory/
├── csv_cleaned/
│   └── (all CSV files)
├── scf_relationships/
│   └── (CSV relationship files)
├── framework_relationships/
│   └── (CSV relationship files)
└── json_output/
    ├── SCF.json
    ├── scf_relationships/
    │   └── (JSON relationship files)
    └── framework_relationships/
        └── (JSON relationship files)
```

## Technical Implementation

### Files Modified
- `app.py` - Added format selection UI and pass format to pipeline
- Already integrated with `main.py run --format` parameter

### Code Changes

**UI Addition:**
```python
self.format_var = tk.StringVar(value="csv")

self.csv_radio = tk.Radiobutton(
    text="CSV only (comma-separated values)",
    variable=self.format_var,
    value="csv"
)

self.json_radio = tk.Radiobutton(
    text="JSON only (JavaScript Object Notation)",
    variable=self.format_var,
    value="json"
)

self.both_radio = tk.Radiobutton(
    text="Both CSV and JSON",
    variable=self.format_var,
    value="both"
)
```

**Pipeline Integration:**
```python
output_format = self.format_var.get()
pipeline.run_pipeline(self.output_path, config_dir, output_format=output_format)
```

## User Benefits

1. **Flexibility** - Users can choose the format that fits their workflow
2. **JSON for APIs** - Direct integration with web apps and databases
3. **CSV for Analysis** - Compatible with Excel, pandas, data analysis tools
4. **Both for Maximum Compatibility** - One extraction, multiple use cases

## Build Status
✅ Ready for PyInstaller build
✅ Tested with all three format options
✅ No additional dependencies required
