#!/usr/bin/env python3

"""
This script builds a YAML file from the cleaned CSV data, following specific
formatting rules for URNs, node hierarchy, and spelling.
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import yaml
from tqdm.auto import tqdm

def replace_us_to_uk_spelling(text: str) -> str:
    """Replaces common US English spellings with UK English spellings."""
    replacements = {
        "organization": "organisation",
        "organizations": "organisations",
        "recognize": "recognise",
        "recognizes": "recognises",
        "analyze": "analyse",
        "analyzes": "analyses",
        "color": "colour",
        "center": "centre",
        "behavior": "behaviour",
        "license": "licence",
        "program": "programme",
    }
    for us_word, uk_word in replacements.items():
        # Use word boundaries to avoid replacing parts of words (e.g., 'item' in 'itemize')
        text = text.replace(f" {us_word} ", f" {uk_word} ")
        text = text.replace(f"({us_word})", f"({uk_word})")
        text = text.replace(f"\'{us_word}\'", f"\'{uk_word}\'")
    return text

def create_yaml_from_csvs(cleaned_dir: Path, output_file: Path, version: str):
    """
    Reads cleaned CSVs and generates a YAML file based on the SCF data structure.
    """
    if not cleaned_dir.is_dir():
        print(f"Error: Cleaned data directory not found at '{cleaned_dir}'", file=sys.stderr)
        sys.exit(1)

    version_urn_format = version.replace('.', '-')
    provider_urn = "wrisc"

    # --- Initialize YAML structure ---
    yaml_data = {
        'urn': f'urn:{provider_urn}:risk:library:scf-{version_urn_format}',
        'locale': 'en',
        'ref_id': f'SCF-{version_urn_format}',
        'name': 'SCF: Secure Controls Framework',
        'description': 'SCF: Secure Controls Framework\n\n  https://securecontrolsframework.com/about-us/',
        'copyright': 'SCF - https://securecontrolsframework.com/terms-conditions/',
        'version': 1,
        'publication_date': '2025-07-15',
        'provider': 'SCF',
        'packager': provider_urn,
        'objects': {
            'framework': {
                'urn': f'urn:{provider_urn}:risk:framework:scf-{version_urn_format}',
                'ref_id': f'SCF-{version_urn_format}',
                'name': 'SCF: Secure Controls Framework',
                'description': 'SCF: Secure Controls Framework\n\n      https://securecontrolsframework.com/about-us/',
                'min_score': 1,
                'max_score': 5,
                'scores_definition': [
                    {'score': 0, 'name': 'Not Performed', 'description': None},
                    {'score': 1, 'name': 'Performed Informally', 'description': None},
                    {'score': 2, 'name': 'Planned & Tracked', 'description': None},
                    {'score': 3, 'name': 'Well Defined', 'description': None},
                    {'score': 4, 'name': 'Quantitatively Controlled', 'description': None},
                    {'score': 5, 'name': 'Continuously Improving', 'description': None},
                ],
                'implementation_groups_definition': [
                    {'ref_id': 'tier1', 'name': 'Tier 1 - Strategic', 'description': None},
                    {'ref_id': 'tier2', 'name': 'Tier 2 - Operational', 'description': None},
                    {'ref_id': 'tier3', 'name': 'Tier 3 - Tactical', 'description': None},
                ],
                'requirement_nodes': []
            }
        }
    }

    # --- Read and process nodes ---
    nodes_df = pd.read_csv(cleaned_dir / 'SCF.csv', dtype=str).fillna('')
    requirement_nodes = []
    node_counter = 2  # Start counting from 2 as per user feedback

    # Sort by domain to ensure consistent ordering
    sorted_domains = sorted(nodes_df['scf_domain'].unique())

    for domain in tqdm(sorted_domains, desc="Processing Domains"):
        group = nodes_df[nodes_df['scf_domain'] == domain]
        
        parent_node_id = f"node{node_counter}"
        parent_urn = f'urn:{provider_urn}:risk:req_node:scf-{version_urn_format}:{parent_node_id}'

        parent_node = {
            'urn': parent_urn,
            'assessable': False,
            'depth': 1,
            'name': domain,
        }
        requirement_nodes.append(parent_node)
        node_counter += 1  # Increment for the parent node

        for record in group.to_dict('records'):
            # The URN for child nodes uses their actual ID, not the counter
            child_urn = f"urn:{provider_urn}:risk:req_node:scf-{version_urn_format}:{record['scf_id']}"
            
            node = {
                'urn': child_urn,
                'assessable': True,
                'depth': 2,
                'parent_urn': parent_urn,
                'ref_id': record['scf_id'],
                'name': record['scf_control'],
                'description': record['secure_controls_framework_scf_control_description'],
                'annotation': record['scf_control_question'],
                'implementation_groups': ['tier1', 'tier2', 'tier3']
            }
            requirement_nodes.append(node)
            node_counter += 1 # Increment for each child node

    yaml_data['objects']['framework']['requirement_nodes'] = requirement_nodes

    # --- Convert to YAML string and perform spelling corrections ---
    yaml_string = yaml.dump(yaml_data, sort_keys=False, indent=2, allow_unicode=True)
    corrected_yaml_string = replace_us_to_uk_spelling(yaml_string)

    # --- Save YAML file ---
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(corrected_yaml_string)

    print(f"✅ Successfully created YAML file at '{output_file}'")

def main():
    """Main function to orchestrate the YAML creation process."""
    parser = argparse.ArgumentParser(description="Builds a YAML file from cleaned SCF data.")
    parser.add_argument("--cleaned-dir", type=Path, default=Path("csv_cleaned"), help="Directory of cleaned entity CSVs.")
    parser.add_argument("-o", "--output-file", type=Path, default=Path("scf-2025-2-1.yaml"), help="Path to save the output YAML file.")
    parser.add_argument("--version", type=str, default="2025.2.1", help="The version of the SCF data.")
    args = parser.parse_args()

    # Adjust output file name based on version
    version_urn_format = args.version.replace('.', '-')
    output_filename = Path(f"scf-{version_urn_format}.yaml")

    create_yaml_from_csvs(args.cleaned_dir, output_filename, args.version)

if __name__ == "__main__":
    main()
