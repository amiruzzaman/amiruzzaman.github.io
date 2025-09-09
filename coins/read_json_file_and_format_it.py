import json

# Read the JSON file
with open("countries.details.json", "r", encoding="utf8") as json_file:
    data = json.load(json_file)

# Convert the Python object to a formatted JSON string with tabs
# Use 'indent="\t"' to specify a tab character for indentation
pretty_json_with_tabs = json.dumps(data, indent="\t")

# Print the formatted string
print(pretty_json_with_tabs)


# Save the formatted JSON back to the same file
with open("countries.details.json", "w", encoding="utf8") as json_file:
    json_file.write(pretty_json_with_tabs)