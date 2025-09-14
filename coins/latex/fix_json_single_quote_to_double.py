import re

with open("list of countries.json", "r", encoding="utf-8") as f:
    text = f.read()

# Replace single quotes around keys and values with double quotes
fixed = re.sub(r"(\w+):", r'"\1":', text)   # keys
fixed = fixed.replace("'", '"')             # values

with open("list_of_countries_fixed.json", "w", encoding="utf-8") as f:
    f.write(fixed)

print("✅ Fixed JSON saved as list_of_countries_fixed.json")
