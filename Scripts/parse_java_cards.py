#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path

CLASS_RE = re.compile(r'public\s+(?:final\s+)?class\s+(\w+)\s+extends\s+CardImpl')
SUPER_CALL_RE = re.compile(
    r'super\s*\(\s*ownerId\s*,\s*setInfo\s*,\s*'
    r'(?:new\s+CardType\[\]\s*\{([^}]+)\}|(\w+))\s*,\s*'
    r'"([^"]*)"'
)
TYPE_ARRAY_RE = re.compile(r'CardType\.(\w+)')
SUBTYPE_RE = re.compile(r'subtype\.add\(SubType\.(\w+)\)')
POWER_RE = re.compile(r'this\.power\s*=\s*new\s+MageInt\s*\(\s*(-?\d+|"([^"]*)")\s*\)')
TOUGHNESS_RE = re.compile(r'this\.toughness\s*=\s*new\s+MageInt\s*\(\s*(-?\d+|"([^"]*)")\s*\)')
LOYALTY_RE = re.compile(r'this\.setLoyalty\s*\(\s*new\s+MageInt\s*\(\s*(-?\d+)\s*\)')
ABILITY_RE = re.compile(r'this\.addAbility\s*\(\s*(?:new\s+)?(\w+(?:\.\w+)?)\s*\(')
KEYWORD_ABILITY_RE = re.compile(r'this\.addAbility\s*\(\s*(\w+)\.getInstance\s*\(\s*\)')
TEXT_ABILITY_RE = re.compile(r'new\s+\w+Ability\(\s*"([^"]+)"')
RULE_TEXT_RE = re.compile(r'"((?:[^"\\]|\\.)*)(?:\s*\.\s*|")')
COMMENT_TEXT_RE = re.compile(r'//\s*(.+)', re.MULTILINE)
ENTERS_BATTLEFIELD_RE = re.compile(r'EntersBattlefieldTriggeredAbility')
DEATH_TRIGGER_RE = re.compile(r'DiesSourceTriggeredAbility|DiesTriggeredAbility')
COMBAT_DAMAGE_RE = re.compile(r'DamagedPlayerEvent|combatDamage')
FLASHBACK_RE = re.compile(r'FlashbackAbility')
DELVE_RE = re.compile(r'DelveAbility')
MENACE_RE = re.compile(r'MenaceAbility')
TRAMPLE_RE = re.compile(r'TrampleAbility')
FLYING_RE = re.compile(r'FlyingAbility|Flying')
DEATHTOUCH_RE = re.compile(r'DeathtouchAbility')
HASTE_RE = re.compile(r'HasteAbility')
FIRST_STRIKE_RE = re.compile(r'FirstStrikeAbility|DoubleStrikeAbility')
LIFELINK_RE = re.compile(r'LifeLinkAbility')
VIGILANCE_RE = re.compile(r'VigilanceAbility')
REACH_RE = re.compile(r'ReachAbility')
SHADOW_RE = re.compile(r'ShadowAbility')
HEXPROOF_RE = re.compile(r'HexproofAbility|Hexproof')
INDESTRUCTIBLE_RE = re.compile(r'IndestructibleAbility')
PROTECTION_RE = re.compile(r'ProtectionAbility')
WARD_RE = re.compile(r'WardAbility')
DOUBLE_STRIKE_RE = re.compile(r'DoubleStrikeAbility')

KEYWORD_MAP = {
    "FlyingAbility": "flying", "MenaceAbility": "menace",
    "TrampleAbility": "trample", "DeathtouchAbility": "deathtouch",
    "HasteAbility": "haste", "FirstStrikeAbility": "first strike",
    "DoubleStrikeAbility": "double strike", "VigilanceAbility": "vigilance",
    "ReachAbility": "reach", "HexproofAbility": "hexproof",
    "IndestructibleAbility": "indestructible", "ShadowAbility": "shadow",
    "LifeLinkAbility": "lifelink", "FlashbackAbility": "flashback",
    "DelveAbility": "delve", "WardAbility": "ward",
}

ABILITY_CLASSES = {
    "EntersBattlefieldTriggeredAbility": "enters_battlefield",
    "DiesSourceTriggeredAbility": "dies_trigger",
    "DiesTriggeredAbility": "dies_trigger",
    "SimpleActivatedAbility": "activated",
    "SimpleStaticAbility": "static",
    "FlashbackAbility": "flashback",
    "DelveAbility": "delve",
    "MonstrosityAbility": "monstrosity",
    "EquipAbility": "equip",
    "ETBDrawCardAbility": "etb_draw",
}


def extract_name_from_filename(filename):
    name = filename.replace(".java", "")
    result = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0 and name[i-1].islower():
            result.append(" ")
        elif ch.isupper() and i > 0 and i < len(name)-1 and name[i+1].islower():
            result.append(" ")
        result.append(ch)
    return "".join(result)


def extract_keywords(content):
    keywords = set()
    for cls, kw in KEYWORD_MAP.items():
        if re.search(r'\b' + cls + r'\b', content):
            keywords.add(kw)
    if re.search(r'\bFlying\b', content) and "flying" not in keywords:
        if 'FlyingAbility' not in content:
            keywords.add("flying")
    if re.search(r'addAbility\(new MenaceAbility', content):
        keywords.add("menace")
    return sorted(keywords)


def extract_abilities(content):
    abilities = []
    for m in KEYWORD_ABILITY_RE.finditer(content):
        cls = m.group(1)
        if cls in KEYWORD_MAP:
            abilities.append({"type": "keyword", "keyword": KEYWORD_MAP[cls]})

    for m in ABILITY_RE.finditer(content):
        cls = m.group(1)
        if "Ability" in cls and cls not in KEYWORD_MAP:
            ability_type = ABILITY_CLASSES.get(cls, "other")
            abilities.append({"type": ability_type, "class": cls})

    for m in TEXT_ABILITY_RE.finditer(content):
        abilities.append({"type": "text", "text": m.group(1)})

    return abilities


def extract_card_from_file(filepath, content):
    class_match = CLASS_RE.search(content)
    if not class_match:
        return None

    class_name = class_match.group(1)
    card = {
        "className": class_name,
        "name": extract_name_from_filename(class_name),
    }

    super_match = SUPER_CALL_RE.search(content)
    if super_match:
        type_str = super_match.group(1) or super_match.group(2)
        mana_cost = super_match.group(3)
        if type_str:
            raw_types = TYPE_ARRAY_RE.findall(type_str)
            card["types"] = [t.capitalize() for t in raw_types]
        card["manaCost"] = mana_cost

    card["subtypes"] = list(set(m.group(1) for m in SUBTYPE_RE.finditer(content)))

    power_match = POWER_RE.search(content)
    if power_match:
        card["power"] = power_match.group(1) or power_match.group(2)

    toughness_match = TOUGHNESS_RE.search(content)
    if toughness_match:
        card["toughness"] = toughness_match.group(1) or toughness_match.group(2)

    loyalty_match = LOYALTY_RE.search(content)
    if loyalty_match:
        card["loyalty"] = int(loyalty_match.group(1))
        card["types"] = card.get("types", []) + ["Planeswalker"]
        card["types"] = list(dict.fromkeys(card["types"]))

    comment_matches = COMMENT_TEXT_RE.findall(content)
    for text in comment_matches:
        text = text.strip()
        if text.startswith("@") or text.startswith("TODO") or text.startswith("FIXME"):
            continue
        if len(text) > 10 and not any(k in text.lower() for k in ["author", "license", "copyright"]):
            if "text" not in card:
                card["text"] = text
            elif "flavorText" not in card:
                card["flavorText"] = text
            break

    keywords = extract_keywords(content)
    if keywords:
        card["keywords"] = keywords

    abilities = extract_abilities(content)
    if abilities:
        card["abilities"] = abilities

    if "types" not in card or not card["types"]:
        return None

    return card


def main():
    parser = argparse.ArgumentParser(description="Parse XMage Java card files into JSON")
    parser.add_argument("--input-dir", default="../../magefree/mage",
                        help="XMage source root (default: ../../magefree/mage)")
    parser.add_argument("--output", default="cards_raw.json",
                        help="Output JSON (default: cards_raw.json)")
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    sets_dir = os.path.join(input_dir, "Mage.Sets", "src", "mage", "cards")
    if not os.path.isdir(sets_dir):
        sets_dir = os.path.join(input_dir, "src", "mage", "cards")
    if not os.path.isdir(sets_dir):
        print(f"Error: Card directory not found. Tried:")
        print(f"  {os.path.join(input_dir, 'Mage.Sets', 'src', 'mage', 'cards')}")
        print(f"  {os.path.join(input_dir, 'src', 'mage', 'cards')}")
        sys.exit(1)

    java_files = []
    for root, dirs, files in os.walk(sets_dir):
        for f in files:
            if f.endswith(".java") and not f.startswith("Card") and not f.startswith("Set"):
                java_files.append(os.path.join(root, f))

    total = len(java_files)
    print(f"Found {total} Java card files in {sets_dir}")

    cards = []
    errors = 0
    for i, filepath in enumerate(java_files):
        if (i + 1) % 500 == 0 or (i + 1) == total:
            print(f"  Processing: {i + 1}/{total} ({(i + 1) * 100 // total}%)")
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            card = extract_card_from_file(filepath, content)
            if card:
                cards.append(card)
        except Exception as e:
            errors += 1

    print(f"\nExtracted {len(cards)} card definitions ({errors} errors)")

    output_path = os.path.abspath(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)
    print(f"Output written to: {output_path}")

    type_counts = {}
    for card in cards:
        for t in card.get("types", []):
            type_counts[t] = type_counts.get(t, 0) + 1

    print("\n--- Summary ---")
    print(f"Total cards: {len(cards)}")
    print("\nBy type:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")


if __name__ == "__main__":
    main()
