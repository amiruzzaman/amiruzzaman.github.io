import json

filename = "ol_spring2026.json"  # your file name

# Load JSON
with open(filename, "r", encoding="utf-8") as f:
    data = json.load(f)

# Iterate through sections (A, B, C, ...)
for section_key, section_value in data.items():
    counter = 1
    
    problems = section_value.get("problems", [])
    
    for group in problems:           # outer list
        for item in group:           # actual rubric items
            item["key"] = f"{section_key}{counter}"
            counter += 1

# Save back to the same file (in-place update)
with open(filename, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Keys added successfully and file updated.")