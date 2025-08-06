import json

# Load JSON from a file or a variable
with open("countries.json", "r", encoding="utf-8") as file:
    data = json.load(file)

# Add 'full_name' field for each item
for country in data:
    country["full_name"] = country["name"]

# Save back to the same or new file
with open("countries_updated.json", "w", encoding="utf-8") as file:
    json.dump(data, file, indent=2, ensure_ascii=False)
