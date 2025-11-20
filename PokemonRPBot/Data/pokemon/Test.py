#!/usr/bin/env python3
import os
import json
import argparse
from collections import OrderedDict

# Define the desired ordering of keys.
# This list forces the stat keys to be between "abilities" and "moves".
# (If a key is not present in a JSON file, it will simply be skipped.)
DESIRED_ORDER = [
    "number",
    "name",
    "types",
    "abilities",
    "base_hp",
    "strength",
    "dexterity",
    "vitality",
    "special",
    "insight",
    "moves",
]

def reorder_keys(original_dict):
    """
    Reorders the dictionary keys to match DESIRED_ORDER.
    Any extra keys not in the DESIRED_ORDER list are appended (sorted alphabetically)
    after the defined keys.
    Returns an OrderedDict.
    """
    new_dict = OrderedDict()
    # First add the keys in the desired order if they exist
    for key in DESIRED_ORDER:
        if key in original_dict:
            new_dict[key] = original_dict[key]
    # Then handle any extra keys not specified in our desired order.
    extra_keys = sorted(set(original_dict.keys()) - set(DESIRED_ORDER))
    for key in extra_keys:
        new_dict[key] = original_dict[key]
    return new_dict

def process_json_files(folder):
    """
    Processes every JSON file in the provided folder by reading its content,
    reordering the keys per the desired order, and writing the updated JSON
    back to the same file.
    """
    for filename in os.listdir(folder):
        if not filename.endswith('.json'):
            continue
        file_path = os.path.join(folder, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as infile:
                data = json.load(infile)
        except Exception as e:
            print(f"Error reading file '{filename}': {e}")
            continue

        new_data = reorder_keys(data)

        try:
            with open(file_path, 'w', encoding='utf-8') as outfile:
                json.dump(new_data, outfile, indent=4)
            print(f"Reordered keys for: {filename}")
        except Exception as e:
            print(f"Error writing file '{filename}': {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Reorder JSON keys so that stat keys are between 'abilities' and 'moves'."
    )
    parser.add_argument("folder", help="Folder containing JSON files to process")
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        print(f"Error: Folder '{args.folder}' does not exist.")
        return

    process_json_files(args.folder)

if __name__ == "__main__":
    main()
