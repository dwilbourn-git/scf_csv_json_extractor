#!/usr/bin/env python3
"""
This script creates a MongoDB-optimized JSON structure with embedded relationships.

The output structure is designed for document databases, embedding related data
directly in the main control documents for optimal query performance.
"""

import argparse
import json
from pathlib import Path
from typing import Optional, Any

import pandas as pd


def clean_value(value: Any) -> Any:
    """Convert pandas NaN values to None (for omission), otherwise return the value."""
    if pd.isna(value):
        return None
    return value


def remove_none_values(d: dict) -> dict:
    """Remove keys with None values from a dictionary."""
    return {k: v for k, v in d.items() if v is not None}


# Import configuration
try:
    from logging_config import get_logger
    from constants import (
        SCF_CSV_FILENAME, DOMAINS_CSV_FILENAME,
        ASSESSMENT_OBJECTIVES_CSV_FILENAME, THREAT_CATALOG_CSV_FILENAME,
        RISK_CATALOG_CSV_FILENAME, EVIDENCE_REQUEST_LIST_CSV_FILENAME
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
    THREAT_CATALOG_CSV_FILENAME = "Threat_Catalog.csv"
    RISK_CATALOG_CSV_FILENAME = "Risk_Catalog.csv"
    EVIDENCE_REQUEST_LIST_CSV_FILENAME = "Evidence_Request_List.csv"


def load_domains(csv_dir: Path) -> dict:
    """Load domains into a dictionary keyed by scf_identifier."""
    domains_file = csv_dir / DOMAINS_CSV_FILENAME
    if not domains_file.exists():
        logger.warning(f"Domains file not found: {domains_file}")
        return {}

    df = pd.read_csv(domains_file, dtype=str, encoding='utf-8')
    domains = {}
    for _, row in df.iterrows():
        scf_identifier = row.get('scf_identifier')
        if pd.notna(scf_identifier):
            domain_data = {
                'identifier': scf_identifier,
                'name': clean_value(row.get('scf_domain')),
                'principle': clean_value(row.get('cybersecurity_data_privacy_by_design_c_p_principles')),
                'principle_intent': clean_value(row.get('principle_intent'))
            }
            domains[scf_identifier] = remove_none_values(domain_data)
    return domains


def load_assessment_objectives(csv_dir: Path) -> dict:
    """Load assessment objectives grouped by scf_id."""
    ao_file = csv_dir / ASSESSMENT_OBJECTIVES_CSV_FILENAME
    if not ao_file.exists():
        logger.warning(f"Assessment objectives file not found: {ao_file}")
        return {}

    df = pd.read_csv(ao_file, dtype=str, encoding='utf-8')
    objectives = {}

    for _, row in df.iterrows():
        scf_id = row.get('scf_id')
        if pd.notna(scf_id):
            if scf_id not in objectives:
                objectives[scf_id] = []

            # Build objective with framework relationships
            obj = {
                'ao_id': clean_value(row.get('scf_ao_id')),
                'objective': clean_value(row.get('scf_assessment_objective')),
                'ao_origin': clean_value(row.get('scf_assessment_objective_ao_origin_s')),
            }

            # Add framework-specific AO relationships
            framework_aos = {}
            if pd.notna(row.get('scf_baseline_aos')):
                framework_aos['scf_baseline'] = True
            if pd.notna(row.get('dhs_ztcf_aos')):
                framework_aos['dhs_ztcf'] = True
            if pd.notna(row.get('nist_800_53_r5_aos')):
                framework_aos['nist_800_53_r5'] = True
            if pd.notna(row.get('nist_800_171_r2_aos')):
                framework_aos['nist_800_171_r2'] = True
            if pd.notna(row.get('nist_800_171_r3_aos')):
                framework_aos['nist_800_171_r3'] = True
            if pd.notna(row.get('nist_800_172_aos')):
                framework_aos['nist_800_172'] = True

            if framework_aos:
                obj['framework_aos'] = framework_aos

            # Remove None values before appending
            objectives[scf_id].append(remove_none_values(obj))

    return objectives


def load_threats(csv_dir: Path) -> dict:
    """Load threat catalog into a dictionary keyed by threat_id."""
    threats_file = csv_dir / THREAT_CATALOG_CSV_FILENAME
    if not threats_file.exists():
        logger.warning(f"Threat catalog file not found: {threats_file}")
        return {}

    df = pd.read_csv(threats_file, dtype=str, encoding='utf-8')
    threats = {}

    for _, row in df.iterrows():
        threat_id = row.get('threat_id')
        if pd.notna(threat_id):
            threat_data = {
                'threat_id': threat_id,
                'threat_grouping': clean_value(row.get('threat_grouping')),
                'threat_name': clean_value(row.get('threat')),
                'threat_description': clean_value(row.get('threat_description'))
            }
            threats[threat_id] = remove_none_values(threat_data)

    return threats


def load_risks(csv_dir: Path) -> dict:
    """Load risk catalog into a dictionary keyed by risk_id."""
    risks_file = csv_dir / RISK_CATALOG_CSV_FILENAME
    if not risks_file.exists():
        logger.warning(f"Risk catalog file not found: {risks_file}")
        return {}

    df = pd.read_csv(risks_file, dtype=str, encoding='utf-8')
    risks = {}

    for _, row in df.iterrows():
        risk_id = row.get('risk_id')
        if pd.notna(risk_id):
            risk_data = {
                'risk_id': risk_id,
                'risk_grouping': clean_value(row.get('risk_grouping')),
                'risk_name': clean_value(row.get('risk')),
                'risk_description': clean_value(row.get('risk_description')),
                'nist_csf_function': clean_value(row.get('nist_csf_function'))
            }
            risks[risk_id] = remove_none_values(risk_data)

    return risks


def load_evidence_requests(csv_dir: Path) -> dict:
    """Load evidence request list into a dictionary keyed by erl_id."""
    erl_file = csv_dir / EVIDENCE_REQUEST_LIST_CSV_FILENAME
    if not erl_file.exists():
        logger.warning(f"Evidence request list file not found: {erl_file}")
        return {}

    df = pd.read_csv(erl_file, dtype=str, encoding='utf-8')
    evidence = {}

    for _, row in df.iterrows():
        erl_id = row.get('erl_id')
        if pd.notna(erl_id):
            evidence_data = {
                'erl_id': erl_id,
                'area_of_focus': clean_value(row.get('area_of_focus')),
                'documentation_artifact': clean_value(row.get('documentation_artifact')),
                'artifact_description': clean_value(row.get('artifact_description'))
            }
            evidence[erl_id] = remove_none_values(evidence_data)

    return evidence


def load_relationships(rel_dir: Path, prefix: str = "scf_to_") -> dict:
    """
    Load all relationship files from a directory into a nested dictionary.

    Returns:
        dict: {scf_id: {relationship_name: [values]}}
    """
    if not rel_dir.exists():
        return {}

    relationships = {}

    for rel_file in rel_dir.glob(f"{prefix}*.csv"):
        rel_name = rel_file.stem.replace(prefix, '')

        df = pd.read_csv(rel_file, dtype=str, encoding='utf-8')

        for _, row in df.iterrows():
            scf_id = row.get('scf_id')
            if pd.notna(scf_id):
                if scf_id not in relationships:
                    relationships[scf_id] = {}

                # Get the value column (usually the second column)
                value_col = [col for col in df.columns if col != 'scf_id'][0]
                value = row.get(value_col)

                if pd.notna(value):
                    if rel_name not in relationships[scf_id]:
                        relationships[scf_id][rel_name] = []
                    relationships[scf_id][rel_name].append(value)

    return relationships


def create_mongodb_structure(
    csv_dir: Path,
    scf_rel_dir: Path,
    framework_rel_dir: Path,
    output_file: Path,
    selected_frameworks: Optional[list[str]] = None
) -> None:
    """
    Creates a MongoDB-optimized JSON structure with embedded relationships.

    Args:
        csv_dir: Directory containing cleaned CSV files.
        scf_rel_dir: Directory containing SCF relationship files.
        framework_rel_dir: Directory containing framework relationship files.
        output_file: Path to save the MongoDB-optimized JSON file.
        selected_frameworks: List of framework IDs to include (e.g., ['scf_to_nist_800_53_rev5']). None means all frameworks.
    """
    logger.info("Loading supporting data...")

    # Load supporting data
    domains = load_domains(csv_dir)
    assessment_objectives = load_assessment_objectives(csv_dir)
    threats = load_threats(csv_dir)
    risks = load_risks(csv_dir)
    evidence_requests = load_evidence_requests(csv_dir)
    scf_relationships = load_relationships(scf_rel_dir, "scf_to_")
    framework_mappings = load_relationships(framework_rel_dir, "scf_to_")

    logger.info(f"Loaded {len(domains)} domains")
    logger.info(f"Loaded assessment objectives for {len(assessment_objectives)} controls")
    logger.info(f"Loaded {len(threats)} threats")
    logger.info(f"Loaded {len(risks)} risks")
    logger.info(f"Loaded {len(evidence_requests)} evidence requests")
    logger.info(f"Loaded SCF relationships for {len(scf_relationships)} controls")
    logger.info(f"Loaded framework mappings for {len(framework_mappings)} controls")

    # Filter frameworks if selection was provided
    if selected_frameworks:
        logger.info(f"Filtering to {len(selected_frameworks)} selected frameworks...")
        filtered_mappings = {}
        for control_id, mappings in framework_mappings.items():
            filtered_control_mappings = {}
            for framework_name, values in mappings.items():
                # Check if this framework is in the selected list
                framework_id = f"scf_to_{framework_name}"
                if framework_id in selected_frameworks:
                    filtered_control_mappings[framework_name] = values
            if filtered_control_mappings:
                filtered_mappings[control_id] = filtered_control_mappings
        framework_mappings = filtered_mappings
        logger.info(f"Filtered to {len(framework_mappings)} controls with selected frameworks")

    # Load main SCF controls
    scf_file = csv_dir / SCF_CSV_FILENAME
    if not scf_file.exists():
        raise RuntimeError(f"SCF controls file not found: {scf_file}")

    logger.info("Building MongoDB-optimized control documents...")
    df = pd.read_csv(scf_file, dtype=str, encoding='utf-8')

    controls = []
    for _, row in df.iterrows():
        scf_id = row.get('scf_id')
        if pd.notna(scf_id):
            # Extract domain identifier from control ID (first 3 chars)
            domain_id = scf_id[:3]

            # Build the control document
            control = {
                '_id': scf_id,  # Use scf_id as MongoDB _id
                'control_id': scf_id,
                'control_number': clean_value(row.get('scf_control')),
                'title': clean_value(row.get('secure_controls_framework_scf_control_description')),

                # Embed domain information
                'domain': domains.get(domain_id, {'identifier': domain_id, 'name': 'Unknown'}),

                # Embed control metadata
                'control_question': clean_value(row.get('scf_control_question')),
                'relative_weight': clean_value(row.get('relative_control_weighting')),

                # Embed business size solutions (only include if values are present)
                'solutions_by_business_size': {
                    k: v for k, v in {
                        'micro_small': row.get('possible_solutions_considerations_micro_small_business_10_staff_bls_firm_size_classes_1_2'),
                        'small': row.get('possible_solutions_considerations_small_business_10_49_staff_bls_firm_size_classes_3_4'),
                        'medium': row.get('possible_solutions_considerations_medium_business_50_249_staff_bls_firm_size_classes_5_6'),
                        'large': row.get('possible_solutions_considerations_large_business_250_999_staff_bls_firm_size_classes_7_8'),
                        'enterprise': row.get('possible_solutions_considerations_enterprise_1_000_staff_bls_firm_size_class_9')
                    }.items() if pd.notna(v)
                },

                # Embed PPTDF applicability
                'pptdf_applicability': {
                    'people': row.get('pptdf_applicability_people') == 'True',
                    'process': row.get('pptdf_applicability_process') == 'True',
                    'technology': row.get('pptdf_applicability_technology') == 'True',
                    'data': row.get('pptdf_applicability_data') == 'True',
                    'facilities': row.get('pptdf_applicability_facilities') == 'True'
                },

                # Embed SCF CORE classifications
                'scf_core': {
                    'esp_level_1_foundational': row.get('scf_core_esp_level_1_foundational') == 'True',
                    'esp_level_2_critical_infrastructure': row.get('scf_core_esp_level_2_critical_infrastructure') == 'True',
                    'esp_level_3_advanced_threats': row.get('scf_core_esp_level_3_advanced_threats') == 'True',
                    'ai_model_deployment': row.get('scf_core_ai_model_deployment') == 'True',
                    'ai_enabled_operations': row.get('scf_core_ai_enabled_operations') == 'True',
                    'fundamentals': row.get('scf_core_fundamentals') == 'True',
                    'mergers_acquisitions_divestitures': row.get('scf_core_mergers_acquisitions_divestitures_ma_d') == 'True',
                    'community_derived': row.get('scf_core_community_derived') == 'True'
                },

                # Embed C|P-CMM maturity levels
                'c_p_cmm': {
                    'level_0_not_performed': row.get('c_p_cmm_0_not_performed') == 'True',
                    'level_1_performed_informally': row.get('c_p_cmm_1_performed_informally') == 'True',
                    'level_2_planned_tracked': row.get('c_p_cmm_2_planned_tracked') == 'True',
                    'level_3_well_defined': row.get('c_p_cmm_3_well_defined') == 'True',
                    'level_4_quantitatively_controlled': row.get('c_p_cmm_4_quantitatively_controlled') == 'True',
                    'level_5_continuously_improving': row.get('c_p_cmm_5_continuously_improving') == 'True'
                },

                # Embed conformity validation
                'conformity_validation_cadence': clean_value(row.get('conformity_validation_cadence')),

                # Embed assessment objectives
                'assessment_objectives': assessment_objectives.get(scf_id, []),

                # Embed full threat details (updated quarterly)
                'threats': [threats[tid] for tid in scf_relationships.get(scf_id, {}).get('control_threat_summary', []) if tid in threats],

                # Embed full risk details (updated quarterly)
                'risks': [risks[rid] for rid in scf_relationships.get(scf_id, {}).get('risk_threat_summary', []) if rid in risks],

                # Embed full evidence request details (updated quarterly)
                'evidence_requests': [evidence_requests[eid] for eid in scf_relationships.get(scf_id, {}).get('evidence_request_list_erl_id', []) if eid in evidence_requests],

                # Embed other SCF relationships (domain, data privacy)
                'scf_relationships': {k: v for k, v in scf_relationships.get(scf_id, {}).items()
                                     if k not in ['control_threat_summary', 'risk_threat_summary', 'evidence_request_list_erl_id']},

                # Embed framework mappings
                'framework_mappings': framework_mappings.get(scf_id, {})
            }

            # Clean up None values, empty strings, empty dictionaries, and empty lists
            control = {k: v for k, v in control.items()
                      if v is not None
                      and v != ""
                      and (not isinstance(v, dict) or v)
                      and (not isinstance(v, list) or v)}

            controls.append(control)

    logger.info(f"Built {len(controls)} MongoDB-optimized control documents")

    # Write to JSON file with proper formatting
    logger.info(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(controls, f, indent=2, ensure_ascii=False)

    logger.info(f"MongoDB-optimized JSON created successfully: {output_file}")
    logger.info(f"  - {len(controls)} control documents")
    logger.info(f"  - Embedded domains, assessment objectives, and all relationships")
    logger.info(f"  - Ready for mongoimport or direct insertion")


def main() -> None:
    """Parses command-line arguments and initiates MongoDB export."""
    parser = argparse.ArgumentParser(
        description="Creates MongoDB-optimized JSON structure with embedded relationships.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=Path("csv_cleaned"),
        help="Directory containing cleaned CSV files"
    )
    parser.add_argument(
        "--scf-rel-dir",
        type=Path,
        default=Path("scf_relationships"),
        help="Directory containing SCF relationship files"
    )
    parser.add_argument(
        "--framework-rel-dir",
        type=Path,
        default=Path("framework_relationships"),
        help="Directory containing framework relationship files"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("scf_mongodb.json"),
        help="Output file for MongoDB-optimized JSON"
    )

    args = parser.parse_args()

    create_mongodb_structure(
        args.csv_dir,
        args.scf_rel_dir,
        args.framework_rel_dir,
        args.output
    )


if __name__ == "__main__":
    main()
