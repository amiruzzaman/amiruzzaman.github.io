import json

# Path to your JSON file
file_path = "C:\\Users\\75MAMIRUZZAM\\OneDrive - West Chester University of PA\\Documents\\Github\\amiruzzaman.github.io\\coins\\images/coins.json"

# Load JSON data
with open(file_path, "r", encoding="utf-8") as f:
    coins = json.load(f)

# Update year and size if they are "none"
for coin in coins:
    if coin.get("year", "").strip().lower() == "none":
        coin["year"] = "0000"
    if coin.get("size", "").strip().lower() == "none":
        coin["size"] = "00"

# Save back to file (pretty printed)
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(coins, f, ensure_ascii=False, indent=4)

print("✅ Updated coins.json successfully!")
