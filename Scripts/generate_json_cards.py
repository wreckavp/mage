#!/usr/bin/env python3
"""
generate_json_cards.py - Generate clean JSON card and set data from raw parsed data.

Takes cards_raw.json and produces validated, deduplicated cards.json and sets.json
files suitable for use in Swift applications.

Usage:
    python3 generate_json_cards.py --input cards_raw.json --output-dir Swift/MageShared/Resources
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict


# Mana cost regex for validation
MANA_COST_REGEX = re.compile(
    r'^(\{[WUBRGCXY0-9]+\}|\{[HW]\}|\{∞\}|\{S\}|\{P\}|\{[WUBRGC]/[WUBRGC]\}|\{[WUBRGC]/[P]\}|\{[12]00\}|\{[1-9][0-9]*\})*$'
)

# Power/toughness patterns
PT_REGEX = re.compile(
    r'^(\*|\d+|\d+\+\d+|\d+-\d+|\d+/\d+|[\d*]+/[\d*]+|\d+\*|\*\d+|\d+\+\*|\*\+\d+|\d+-\*|\*-\d+|X/[\d*]+|[\d*]+/X|\d+\^?\+?)$'
)

# Valid set codes
VALID_SET_CODES = re.compile(r'^[A-Z0-9]{2,6}$')


def validate_mana_cost(mana_cost):
    """Validate mana cost format."""
    if not mana_cost:
        return True  # Empty is valid (lands, etc.)
    return bool(MANA_COST_REGEX.match(mana_cost))


def validate_power_toughness(value):
    """Validate power or toughness format."""
    if not value:
        return True  # Empty is valid
    return bool(PT_REGEX.match(value))


def normalize_card(card):
    """Normalize card data types and formats."""
    normalized = {}
    
    # Required fields
    normalized["name"] = card.get("name", "Unknown")
    normalized["manaCost"] = card.get("manaCost", "")
    normalized["types"] = card.get("types", [])
    normalized["subtypes"] = card.get("subtypes", [])
    normalized["supertypes"] = card.get("supertypes", [])
    normalized["rarity"] = card.get("rarity", "common").lower()
    
    # Optional fields
    normalized["power"] = card.get("power")
    normalized["toughness"] = card.get("toughness")
    normalized["loyalty"] = card.get("loyalty")
    normalized["text"] = card.get("text", "")
    normalized["flavorText"] = card.get("flavorText", "")
    normalized["setCode"] = card.get("setCode", "")
    normalized["cardNumber"] = card.get("cardNumber", "")
    normalized["className"] = card.get("className", "")
    normalized["keywords"] = card.get("keywords", [])
    normalized["abilities"] = card.get("abilities", [])
    
    # Normalize power/toughness as strings
    if normalized["power"] is not None:
        normalized["power"] = str(normalized["power"])
    if normalized["toughness"] is not None:
        normalized["toughness"] = str(normalized["toughness"])
    if normalized["loyalty"] is not None:
        normalized["loyalty"] = str(normalized["loyalty"])
    
    # Ensure types are arrays
    for field in ["types", "subtypes", "supertypes"]:
        if not isinstance(normalized[field], list):
            normalized[field] = []
    
    # Normalize rarity
    valid_rarities = {"common", "uncommon", "rare", "mythic", "special", "bonus"}
    if normalized["rarity"] not in valid_rarities:
        normalized["rarity"] = "common"
    
    return normalized


def deduplicate_cards(cards):
    """Deduplicate cards by name, keeping the most recent version."""
    seen = {}
    deduped = []
    
    for card in cards:
        name = card.get("name", "")
        if not name:
            continue
        
        if name in seen:
            # Keep the version with more information or the later one
            existing = seen[name]
            existing_fields = sum(1 for v in existing.values() if v)
            new_fields = sum(1 for v in card.values() if v)
            
            if new_fields > existing_fields:
                # Replace with more complete version
                idx = deduped.index(existing)
                deduped[idx] = card
                seen[name] = card
        else:
            seen[name] = card
            deduped.append(card)
    
    return deduped


def generate_set_metadata(cards):
    """Generate set metadata from card data."""
    sets = defaultdict(lambda: {"cards": [], "name": "", "code": ""})
    
    for card in cards:
        set_code = card.get("setCode", "")
        if set_code:
            sets[set_code]["cards"].append(card.get("name", ""))
            if not sets[set_code]["code"]:
                sets[set_code]["code"] = set_code
    
    set_list = []
    for code, data in sorted(sets.items()):
        set_info = {
            "code": code,
            "name": data.get("name", code),
            "cardCount": len(data["cards"]),
            "cards": sorted(set(data["cards"]))
        }
        set_list.append(set_info)
    
    return set_list


def main():
    parser = argparse.ArgumentParser(
        description="Generate clean JSON card and set data from raw parsed data"
    )
    parser.add_argument(
        "--input",
        default="cards_raw.json",
        help="Input JSON file (default: cards_raw.json)"
    )
    parser.add_argument(
        "--output-dir",
        default="Swift/MageShared/Resources",
        help="Output directory (default: Swift/MageShared/Resources)"
    )
    
    args = parser.parse_args()
    
    input_path = os.path.abspath(args.input)
    if not os.path.isfile(input_path):
        print(f"Error: Input file not found: {input_path}")
        print("Please run parse_java_cards.py first to generate the input file.")
        sys.exit(1)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        raw_cards = json.load(f)
    
    print(f"Loaded {len(raw_cards)} raw cards from {input_path}")
    
    # Normalize all cards
    print("Normalizing card data...")
    normalized_cards = [normalize_card(card) for card in raw_cards]
    
    # Deduplicate
    print("Deduplicating cards...")
    deduped_cards = deduplicate_cards(normalized_cards)
    print(f"After deduplication: {len(deduped_cards)} cards")
    
    # Validate
    validation_errors = []
    for i, card in enumerate(deduped_cards):
        if not card.get("name"):
            validation_errors.append(f"Card {i}: Missing name")
        if not validate_mana_cost(card.get("manaCost", "")):
            validation_errors.append(f"Card {card.get('name', i)}: Invalid mana cost: {card.get('manaCost')}")
        if card.get("power") and not validate_power_toughness(card["power"]):
            validation_errors.append(f"Card {card.get('name', i)}: Invalid power: {card['power']}")
        if card.get("toughness") and not validate_power_toughness(card["toughness"]):
            validation_errors.append(f"Card {card.get('name', i)}: Invalid toughness: {card['toughness']}")
    
    if validation_errors:
        print(f"\nValidation warnings ({len(validation_errors)}):")
        for err in validation_errors[:10]:
            print(f"  - {err}")
        if len(validation_errors) > 10:
            print(f"  ... and {len(validation_errors) - 10} more")
    
    # Generate set metadata
    print("Generating set metadata...")
    sets = generate_set_metadata(deduped_cards)
    
    # Create output directory
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Write cards.json
    cards_path = os.path.join(output_dir, "cards.json")
    with open(cards_path, 'w', encoding='utf-8') as f:
        json.dump(deduped_cards, f, indent=2, ensure_ascii=False)
    print(f"Generated: {cards_path}")
    
    # Write sets.json
    sets_path = os.path.join(output_dir, "sets.json")
    with open(sets_path, 'w', encoding='utf-8') as f:
        json.dump(sets, f, indent=2, ensure_ascii=False)
    print(f"Generated: {sets_path}")
    
    # Print summary
    print(f"\n--- Summary ---")
    print(f"Total cards: {len(deduped_cards)}")
    print(f"Total sets: {len(sets)}")
    
    # Type breakdown
    type_counts = defaultdict(int)
    rarity_counts = defaultdict(int)
    for card in deduped_cards:
        for t in card.get("types", []):
            type_counts[t] += 1
        rarity_counts[card.get("rarity", "unknown")] += 1
    
    print("\nBy type:")
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count}")
    
    print("\nBy rarity:")
    for r, count in sorted(rarity_counts.items()):
        print(f"  {r}: {count}")
    
    print(f"\nOutput directory: {output_dir}")


if __name__ == "__main__":
    main()
