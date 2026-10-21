#!/usr/bin/env python3
"""
generate_swift_cards.py - Generate Swift card definitions from parsed card data.

Takes cards_raw.json and generates CardDefinitions.swift and CardRepository.swift
with Swift struct definitions and lookup functionality.

Usage:
    python3 generate_swift_cards.py --input cards_raw.json --output-dir Swift/MageShared/Sources/MageShared/Cards/Generated
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


# Swift reserved keywords that need escaping
SWIFT_KEYWORDS = {
    "associatedtype", "class", "deinit", "enum", "extension", "func", "import",
    "init", "inout", "internal", "let", "operator", "private", "protocol", "public",
    "static", "struct", "subtotal", "subscript", "typealias", "var", "break",
    "case", "continue", "default", "defer", "do", "else", "fallthrough", "for",
    "guard", "if", "in", "repeat", "return", "switch", "where", "while",
    "as", "catch", "dynamicType", "false", "is", "nil", "rethrows", "super",
    "self", "Self", "throw", "throws", "true", "try", "__COLUMN__", "__FILE__",
    "__FUNCTION__", "__LINE__"
}

# Mana cost to Swift property name mapping
MANA_SYMBOL_MAP = {
    "{W}": "white",
    "{U}": "blue",
    "{B}": "black",
    "{R}": "red",
    "{G}": "green",
    "{C}": "colorless",
    "{X}": "x",
    "{Y}": "y",
    "{Z}": "z",
    "{0}": "zero",
    "{1}": "one",
    "{2}": "two",
    "{3}": "three",
    "{4}": "four",
    "{5}": "five",
    "{6}": "six",
    "{7}": "seven",
    "{8}": "eight",
    "{9}": "nine",
    "{10}": "ten",
    "{11}": "eleven",
    "{12}": "twelve",
    "{13}": "thirteen",
    "{14}": "fourteen",
    "{15}": "fifteen",
    "{16}": "sixteen",
    "{17}": "seventeen",
    "{18}": "eighteen",
    "{19}": "nineteen",
    "{20}": "twenty",
    "{100}": "hundred",
    "{∞}": "infinity",
    "{HW}": "halfWhite",
    "{HU}": "halfBlue",
    "{HR}": "halfRed",
    "{HP}": "halfPurple",
    "{S}": "snow",
    "{P}": "phyrexian",
    "{W/P}": "whitePhyrexian",
    "{U/P}": "bluePhyrexian",
    "{B/P}": "blackPhyrexian",
    "{R/P}": "redPhyrexian",
    "{G/P}": "greenPhyrexian",
}


def sanitize_swift_name(name):
    """Convert a card name to a valid Swift identifier."""
    # Remove non-alphanumeric characters
    sanitized = re.sub(r'[^a-zA-Z0-9]', '', name)
    
    # Ensure it starts with a letter
    if sanitized and sanitized[0].isdigit():
        sanitized = "card" + sanitized
    
    # Check if it's a reserved keyword
    if sanitized.lower() in SWIFT_KEYWORDS:
        sanitized = sanitized + "Card"
    
    return sanitized if sanitized else "unnamedCard"


def swift_string_literal(s):
    """Escape a string for use in Swift string literal."""
    if s is None:
        return '""'
    s = s.replace('\\', '\\\\')
    s = s.replace('"', '\\"')
    s = s.replace('\n', '\\n')
    s = s.replace('\r', '\\r')
    s = s.replace('\t', '\\t')
    return f'"{s}"'


def generate_card_definition(card, index):
    """Generate Swift code for a single card definition."""
    name = card.get("name", f"UnknownCard{index}")
    swift_name = sanitize_swift_name(name)
    
    mana_cost = card.get("manaCost", "")
    types = card.get("types", [])
    subtypes = card.get("subtypes", [])
    supertypes = card.get("supertypes", [])
    power = card.get("power")
    toughness = card.get("toughness")
    loyalty = card.get("loyalty")
    text = card.get("text", "")
    flavor_text = card.get("flavorText", "")
    rarity = card.get("rarity", "common")
    set_code = card.get("setCode", "")
    card_number = card.get("cardNumber", "")
    
    # Build the card type string
    type_string = " ".join(supertypes + types)
    if subtypes:
        type_string += " — " + " ".join(subtypes)
    
    # Build the Swift code
    lines = []
    lines.append(f"    /// {name}")
    lines.append(f"    static let {swift_name} = CardDefinition(")
    lines.append(f"        name: {swift_string_literal(name)},")
    lines.append(f"        manaCost: {swift_string_literal(mana_cost)},")
    lines.append(f"        type: {swift_string_literal(type_string)},")
    
    if power is not None and toughness is not None:
        lines.append(f"        power: {swift_string_literal(power)},")
        lines.append(f"        toughness: {swift_string_literal(toughness)},")
    else:
        lines.append(f"        power: nil,")
        lines.append(f"        toughness: nil,")
    
    if loyalty is not None:
        lines.append(f"        loyalty: {swift_string_literal(loyalty)},")
    else:
        lines.append(f"        loyalty: nil,")
    
    lines.append(f"        rarity: {swift_string_literal(rarity)},")
    lines.append(f"        setCode: {swift_string_literal(set_code)},")
    lines.append(f"        cardNumber: {swift_string_literal(card_number)},")
    lines.append(f"        text: {swift_string_literal(text)},")
    lines.append(f"        flavorText: {swift_string_literal(flavor_text)}")
    lines.append(f"    )")
    
    return "\n".join(lines)


def generate_card_definitions(cards):
    """Generate the full CardDefinitions.swift file content."""
    header = '''//
//  CardDefinitions.swift
//  MageShared
//
//  Auto-generated by generate_swift_cards.py
//  DO NOT EDIT - Generated from XMage card data
//

import Foundation

public struct CardDefinition {
    public let name: String
    public let manaCost: String
    public let type: String
    public let power: String?
    public let toughness: String?
    public let loyalty: String?
    public let rarity: String
    public let setCode: String
    public let cardNumber: String
    public let text: String
    public let flavorText: String
    
    public init(
        name: String,
        manaCost: String,
        type: String,
        power: String? = nil,
        toughness: String? = nil,
        loyalty: String? = nil,
        rarity: String = "common",
        setCode: String = "",
        cardNumber: String = "",
        text: String = "",
        flavorText: String = ""
    ) {
        self.name = name
        self.manaCost = manaCost
        self.type = type
        self.power = power
        self.toughness = toughness
        self.loyalty = loyalty
        self.rarity = rarity
        self.setCode = setCode
        self.cardNumber = cardNumber
        self.text = text
        self.flavorText = flavorText
    }
}

extension CardDefinition {
'''
    
    footer = '}'
    
    definitions = []
    for i, card in enumerate(cards):
        definitions.append(generate_card_definition(card, i))
    
    return header + "\n\n".join(definitions) + "\n" + footer


def generate_repository(cards):
    """Generate CardRepository.swift with lookup functionality."""
    # Build name index
    name_index = {}
    set_index = {}
    type_index = {}
    
    for card in cards:
        name = card.get("name", "")
        swift_name = sanitize_swift_name(name)
        
        if name:
            name_index[name] = swift_name
        
        set_code = card.get("setCode", "")
        if set_code:
            if set_code not in set_index:
                set_index[set_code] = []
            set_index[set_code].append(swift_name)
        
        for t in card.get("types", []):
            if t not in type_index:
                type_index[t] = []
            type_index[t].append(swift_name)
    
    header = '''//
//  CardRepository.swift
//  MageShared
//
//  Auto-generated by generate_swift_cards.py
//  DO NOT EDIT - Generated from XMage card data
//

import Foundation

public struct CardRepository {
    private let cardsByName: [String: CardDefinition]
    private let cardsBySet: [String: [CardDefinition]]
    private let cardsByType: [String: [CardDefinition]]
    
    public static let shared = CardRepository()
    
    private init() {
        var byName: [String: CardDefinition] = [:]
        var bySet: [String: [CardDefinition]] = [:]
        var byType: [String: [CardDefinition]] = [:]
        
        let allCards = CardDefinitions.allCards
        
        for card in allCards {
            byName[card.name.lowercased()] = card
            
            if !card.setCode.isEmpty {
                if bySet[card.setCode] == nil {
                    bySet[card.setCode] = []
                }
                bySet[card.setCode]?.append(card)
            }
            
            let types = card.type.components(separatedBy: " — ").first ?? card.type
            for typeName in types.components(separatedBy: " ") {
                let trimmed = typeName.trimmingCharacters(in: .whitespaces)
                if !trimmed.isEmpty {
                    if byType[trimmed] == nil {
                        byType[trimmed] = []
                    }
                    byType[trimmed]?.append(card)
                }
            }
        }
        
        self.cardsByName = byName
        self.cardsBySet = bySet
        self.cardsByType = byType
    }
    
    public func card(named name: String) -> CardDefinition? {
        return cardsByName[name.lowercased()]
    }
    
    public func cards(inSet setCode: String) -> [CardDefinition] {
        return cardsBySet[setCode] ?? []
    }
    
    public func cards(ofType type: String) -> [CardDefinition] {
        return cardsByType[type] ?? []
    }
    
    public func search(query: String) -> [CardDefinition] {
        let lowercased = query.lowercased()
        return cardsByName.values.filter { card in
            card.name.lowercased().contains(lowercased) ||
            card.text.lowercased().contains(lowercased)
        }
    }
    
    public var allCardNames: [String] {
        return Array(cardsByName.keys).sorted()
    }
    
    public var totalCount: Int {
        return cardsByName.count
    }
}
'''
    
    return header


def main():
    parser = argparse.ArgumentParser(
        description="Generate Swift card definitions from parsed card data"
    )
    parser.add_argument(
        "--input",
        default="cards_raw.json",
        help="Input JSON file (default: cards_raw.json)"
    )
    parser.add_argument(
        "--output-dir",
        default="Swift/MageShared/Sources/MageShared/Cards/Generated",
        help="Output directory (default: Swift/MageShared/Sources/MageShared/Cards/Generated)"
    )
    
    args = parser.parse_args()
    
    input_path = os.path.abspath(args.input)
    if not os.path.isfile(input_path):
        print(f"Error: Input file not found: {input_path}")
        print("Please run parse_java_cards.py first to generate the input file.")
        sys.exit(1)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        cards = json.load(f)
    
    print(f"Loaded {len(cards)} cards from {input_path}")
    
    # Create output directory
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate CardDefinitions.swift
    definitions_content = generate_card_definitions(cards)
    definitions_path = os.path.join(output_dir, "CardDefinitions.swift")
    with open(definitions_path, 'w', encoding='utf-8') as f:
        f.write(definitions_content)
    print(f"Generated: {definitions_path}")
    
    # Generate CardRepository.swift
    repository_content = generate_repository(cards)
    repository_path = os.path.join(output_dir, "CardRepository.swift")
    with open(repository_path, 'w', encoding='utf-8') as f:
        f.write(repository_content)
    print(f"Generated: {repository_path}")
    
    # Print statistics
    names = [c.get("name", "") for c in cards]
    unique_names = set(names)
    
    print(f"\n--- Summary ---")
    print(f"Total cards: {len(cards)}")
    print(f"Unique card names: {len(unique_names)}")
    print(f"Output directory: {output_dir}")
    print(f"Files generated:")
    print(f"  - CardDefinitions.swift ({len(cards)} card definitions)")
    print(f"  - CardRepository.swift (lookup by name, set, type)")


if __name__ == "__main__":
    main()
