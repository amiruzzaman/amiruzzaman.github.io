import json
import re

# Path to your JSON file
file_path = "./images/coins.json"

# Load JSON data
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Regex to match a 4-digit year inside parentheses
year_pattern = re.compile(r"\((\d{4})\)")

# Iterate through each object and update 'year' if found in 'note'
for obj in data:
    note = obj.get("note", "")
    match = year_pattern.search(note)
    if match:
        obj["year"] = match.group(1)  # set year to the matched number

# Save the updated JSON back to file
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("Year fields updated successfully!")
