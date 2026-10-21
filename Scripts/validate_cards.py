#!/usr/bin/env python3
"""
validate_cards.py - Validate generated card data and produce a validation report.

Checks cards.json and sets.json for required fields, valid formats, and consistency.
Outputs validation_report.json with detailed results and statistics.

Usage:
    python3 validate_cards.py --cards cards.json --sets sets.json
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict


# Mana cost regex pattern
MANA_COST_PATTERN = re.compile(
    r'^(\{[WUBRGCXY0-9]+\}|\{[HW]\}|\{∞\}|\{S\}|\{P\}|\{[WUBRGC]/[WUBRGC]\}|\{[WUBRGC]/P\}|\{[12]00\}|\{[1-9][0-9]*\})*$'
)

# Power/toughness regex pattern
PT_PATTERN = re.compile(
    r'^(\*|\d+|\d+\+\d+|\d+-\d+|\d+/\d+|[\d*]+/[\d*]+|\d+\*|\*\d+|\d+\+[\d*]|[\d*]+\+\d+|\d+-[\d*]|[\d*]+-\d+|X/[\d*]+|[\d*]+/X|\d+\^?\+?)$'
)

# Valid set codes
SET_CODE_PATTERN = re.compile(r'^[A-Z0-9]{2,6}$')

# Required card fields
REQUIRED_FIELDS = ["name", "manaCost", "types", "rarity"]

# Valid rarities
VALID_RARITIES = {"common", "uncommon", "rare", "mythic", "special", "bonus"}

# Valid card types
VALID_TYPES = {
    "Creature", "Instant", "Sorcery", "Artifact", "Enchantment",
    "Planeswalker", "Land", "Tribal"
}

# Valid supertypes
VALID_SUPERTYPES = {"Legendary", "Basic", "Ongoing", "Snow", "World"}


def validate_mana_cost(mana_cost):
    """Validate mana cost format."""
    if not mana_cost:
        return True, "Empty mana cost (valid for lands)"
    if MANA_COST_PATTERN.match(mana_cost):
        return True, "Valid"
    return False, f"Invalid mana cost format: {mana_cost}"


def validate_power_toughness(value, field_name):
    """Validate power or toughness format."""
    if not value:
        return True, f"Empty {field_name} (valid for non-creatures)"
    if PT_PATTERN.match(str(value)):
        return True, "Valid"
    return False, f"Invalid {field_name} format: {value}"


def validate_card(card, index):
    """Validate a single card and return list of issues."""
    issues = []
    
    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in card or card[field] is None:
            issues.append({
                "severity": "error",
                "field": field,
                "message": f"Missing required field: {field}"
            })
    
    # Validate name
    name = card.get("name", "")
    if not name:
        issues.append({
            "severity": "error",
            "field": "name",
            "message": "Card name is empty"
        })
    elif len(name) > 200:
        issues.append({
            "severity": "warning",
            "field": "name",
            "message": f"Card name unusually long ({len(name)} chars)"
        })
    
    # Validate mana cost
    mana_cost = card.get("manaCost", "")
    is_valid, message = validate_mana_cost(mana_cost)
    if not is_valid:
        issues.append({
            "severity": "error",
            "field": "manaCost",
            "message": message
        })
    
    # Validate power/toughness
    power = card.get("power")
    toughness = card.get("toughness")
    if power is not None:
        is_valid, message = validate_power_toughness(power, "power")
        if not is_valid:
            issues.append({
                "severity": "error",
                "field": "power",
                "message": message
            })
    if toughness is not None:
        is_valid, message = validate_power_toughness(toughness, "toughness")
        if not is_valid:
            issues.append({
                "severity": "error",
                "field": "toughness",
                "message": message
            })
    
    # Validate types
    types = card.get("types", [])
    if not types:
        issues.append({
            "severity": "warning",
            "field": "types",
            "message": "No types specified"
        })
    else:
        for t in types:
            if t not in VALID_TYPES and t not in VALID_SUPERTYPES:
                issues.append({
                    "severity": "warning",
                    "field": "types",
                    "message": f"Unknown type: {t}"
                })
    
    # Validate rarity
    rarity = card.get("rarity", "")
    if rarity and rarity not in VALID_RARITIES:
        issues.append({
            "severity": "warning",
            "field": "rarity",
            "message": f"Unknown rarity: {rarity}"
        })
    
    # Validate set code
    set_code = card.get("setCode", "")
    if set_code and not SET_CODE_PATTERN.match(set_code):
        issues.append({
            "severity": "warning",
            "field": "setCode",
            "message": f"Invalid set code format: {set_code}"
        })
    
    return issues


def check_duplicate_names(cards):
    """Check for duplicate card names."""
    name_counts = defaultdict(list)
    for i, card in enumerate(cards):
        name = card.get("name", "")
        if name:
            name_counts[name].append(i)
    
    duplicates = {}
    for name, indices in name_counts.items():
        if len(indices) > 1:
            duplicates[name] = indices
    
    return duplicates


def generate_statistics(cards):
    """Generate card statistics."""
    stats = {
        "total": len(cards),
        "by_type": defaultdict(int),
        "by_rarity": defaultdict(int),
        "by_set": defaultdict(int),
        "with_power_toughness": 0,
        "with_loyalty": 0,
        "with_text": 0,
        "with_flavor_text": 0,
        "avg_name_length": 0,
        "avg_mana_cost_length": 0,
    }
    
    total_name_length = 0
    total_mana_length = 0
    
    for card in cards:
        # Types
        for t in card.get("types", []):
            stats["by_type"][t] += 1
        
        # Rarity
        rarity = card.get("rarity", "unknown")
        stats["by_rarity"][rarity] += 1
        
        # Set
        set_code = card.get("setCode", "")
        if set_code:
            stats["by_set"][set_code] += 1
        
        # Optional fields
        if card.get("power") and card.get("toughness"):
            stats["with_power_toughness"] += 1
        if card.get("loyalty"):
            stats["with_loyalty"] += 1
        if card.get("text"):
            stats["with_text"] += 1
        if card.get("flavorText"):
            stats["with_flavor_text"] += 1
        
        # Lengths
        total_name_length += len(card.get("name", ""))
        total_mana_length += len(card.get("manaCost", ""))
    
    if cards:
        stats["avg_name_length"] = round(total_name_length / len(cards), 1)
        stats["avg_mana_cost_length"] = round(total_mana_length / len(cards), 1)
    
    # Convert defaultdicts to regular dicts for JSON
    stats["by_type"] = dict(stats["by_type"])
    stats["by_rarity"] = dict(stats["by_rarity"])
    stats["by_set"] = dict(stats["by_set"])
    
    return stats


def validate_sets(sets_data):
    """Validate sets data."""
    issues = []
    
    if not isinstance(sets_data, list):
        issues.append({
            "severity": "error",
            "message": "sets.json must be a JSON array"
        })
        return issues
    
    for i, s in enumerate(sets_data):
        if "code" not in s:
            issues.append({
                "severity": "error",
                "message": f"Set {i}: Missing 'code' field"
            })
        elif not SET_CODE_PATTERN.match(s["code"]):
            issues.append({
                "severity": "warning",
                "message": f"Set {i}: Invalid set code format: {s['code']}"
            })
        
        if "name" not in s:
            issues.append({
                "severity": "warning",
                "message": f"Set {i}: Missing 'name' field"
            })
        
        if "cardCount" not in s:
            issues.append({
                "severity": "warning",
                "message": f"Set {i}: Missing 'cardCount' field"
            })
    
    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Validate generated card data and produce a validation report"
    )
    parser.add_argument(
        "--cards",
        default="cards.json",
        help="Cards JSON file (default: cards.json)"
    )
    parser.add_argument(
        "--sets",
        default="sets.json",
        help="Sets JSON file (default: sets.json)"
    )
    
    args = parser.parse_args()
    
    report = {
        "status": "pass",
        "cards_file": args.cards,
        "sets_file": args.sets,
        "errors": [],
        "warnings": [],
        "duplicates": {},
        "statistics": {},
        "set_validation": []
    }
    
    # Validate cards
    cards_path = os.path.abspath(args.cards)
    if not os.path.isfile(cards_path):
        print(f"Error: Cards file not found: {cards_path}")
        print("Please run generate_json_cards.py first to generate the cards file.")
        sys.exit(1)
    
    with open(cards_path, 'r', encoding='utf-8') as f:
        cards = json.load(f)
    
    print(f"Validating {len(cards)} cards from {cards_path}")
    
    all_issues = []
    for i, card in enumerate(cards):
        issues = validate_card(card, i)
        for issue in issues:
            issue["card_index"] = i
            issue["card_name"] = card.get("name", f"Unknown-{i}")
            all_issues.append(issue)
    
    # Separate errors and warnings
    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]
    
    report["errors"] = errors
    report["warnings"] = warnings
    
    # Check for duplicates
    duplicates = check_duplicate_names(cards)
    report["duplicates"] = {name: indices for name, indices in duplicates.items()}
    
    # Generate statistics
    statistics = generate_statistics(cards)
    report["statistics"] = statistics
    
    # Validate sets
    sets_path = os.path.abspath(args.sets)
    if os.path.isfile(sets_path):
        with open(sets_path, 'r', encoding='utf-8') as f:
            sets_data = json.load(f)
        
        set_issues = validate_sets(sets_data)
        report["set_validation"] = set_issues
        print(f"Validated {len(sets_data)} sets from {sets_path}")
    else:
        print(f"Warning: Sets file not found: {sets_path}")
        report["set_validation"] = [{
            "severity": "warning",
            "message": f"Sets file not found: {sets_path}"
        }]
    
    # Determine overall status
    if errors:
        report["status"] = "fail"
    elif warnings or duplicates:
        report["status"] = "pass_with_warnings"
    
    # Write report
    report_path = os.path.join(os.path.dirname(cards_path) or '.', "validation_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nValidation report written to: {report_path}")
    
    # Print summary
    print(f"\n--- Validation Summary ---")
    print(f"Status: {report['status'].upper()}")
    print(f"Total cards: {statistics['total']}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Duplicate names: {len(duplicates)}")
    
    if statistics['by_type']:
        print(f"\nBy type:")
        for t, count in sorted(statistics['by_type'].items()):
            print(f"  {t}: {count}")
    
    if statistics['by_rarity']:
        print(f"\nBy rarity:")
        for r, count in sorted(statistics['by_rarity'].items()):
            print(f"  {r}: {count}")
    
    if statistics['by_set']:
        print(f"\nBy set (top 10):")
        sorted_sets = sorted(statistics['by_set'].items(), key=lambda x: x[1], reverse=True)[:10]
        for s, count in sorted_sets:
            print(f"  {s}: {count}")
    
    # Exit with error code if there are errors
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
