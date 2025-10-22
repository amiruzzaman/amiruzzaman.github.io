import json
import os
import webbrowser

# ==========================
# File Paths and Constants
# ==========================
INPUT_JSON = "images/coins.json"   # your input path
OUTPUT_JSON = "coins.updated.json"
OUTPUT_HTML = "coins_table.html"
HOST = "https://amiruzzaman.github.io/coins"  # base host URL


# ==========================
# Load Data
# ==========================
with open(INPUT_JSON, "r", encoding="utf-8") as f:
    coins = json.load(f)

# ==========================
# Group by country
# ==========================
country_groups = {}
for coin in coins:
    country = coin.get("country")
    if country not in country_groups:
        country_groups[country] = []
    country_groups[country].append(coin)

# ==========================
# Assign/Propagate Box Values
# ==========================
no_box_countries = []
for country, items in country_groups.items():
    box_value = None
    for item in items:
        if "box" in item and item["box"]:
            box_value = item["box"]
            break
    if box_value:
        for item in items:
            item["box"] = box_value
    else:
        no_box_countries.append(country)

# ==========================
# Add URL field for each coin
# ==========================
for coin in coins:
    country = coin.get("country", "").replace(" ", "%20")
    image_name = coin.get("image", "")
    coin_id = os.path.splitext(image_name)[0]  # remove extension
    if country and image_name:
        coin["url"] = f"{HOST}/display.html?country={country}&coin={coin_id}"
    else:
        coin["url"] = "N/A"

# ==========================
# Save Updated JSON
# ==========================
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(coins, f, indent=2, ensure_ascii=False)

# ==========================
# Collect all unique keys
# ==========================
all_keys = set()
for coin in coins:
    all_keys.update(coin.keys())
all_keys = sorted(all_keys)

# ==========================
# Build HTML
# ==========================
html_header = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Coins Table View</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;background:#f6f8fa;margin:20px;color:#111;}}
h1{{margin-top:0;}}
table{{border-collapse:collapse;width:100%;font-size:14px;}}
th,td{{border:1px solid #ccc;padding:6px 10px;vertical-align:top;}}
th{{background:#eee;position:sticky;top:0;}}
tr:nth-child(even){{background:#fafafa;}}
.badge{{display:inline-block;padding:2px 6px;border-radius:4px;font-size:12px;}}
.badge.ok{{background:#d9f9e4;color:#0a5c2d;}}
.badge.miss{{background:#ffeaea;color:#b30000;}}
a{{color:#0645ad;text-decoration:none;}}
a:hover{{text-decoration:underline;}}
</style>
</head>
<body>
<h1>Coins Data (Updated)</h1>
<p><strong>Updated JSON file:</strong> {output_json}</p>
""".format(output_json=OUTPUT_JSON)

# Create table with dynamic columns
html_table = "<table>\n<tr>" + "".join(f"<th>{k}</th>" for k in all_keys) + "</tr>\n"

for coin in coins:
    html_table += "<tr>"
    for k in all_keys:
        value = coin.get(k, "N/A")
        if isinstance(value, str):
            # make web URLs clickable
            if value.startswith("http"):
                value = f'<a href="{value}" target="_blank">{value}</a>'
        html_table += f"<td>{value}</td>"
    html_table += "</tr>\n"

html_table += "</table>\n"

# ==========================
# Countries Without Box Value
# ==========================
html_table += "<h2>Countries without box value</h2>\n<ul>"
if no_box_countries:
    for c in no_box_countries:
        html_table += f"<li><span class='badge miss'>{c}</span></li>"
else:
    html_table += "<li><span class='badge ok'>All countries have box values</span></li>"
html_table += "</ul>"

html_footer = "</body></html>"

# ==========================
# Write HTML Output
# ==========================
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_header + html_table + html_footer)

# ==========================
# Open in Browser
# ==========================
abs_path = os.path.abspath(OUTPUT_HTML)
webbrowser.open(f"file://{abs_path}")

print(f"\n✅ Updated JSON saved as: {OUTPUT_JSON}")
print(f"✅ HTML table saved as: {OUTPUT_HTML}")
print(f"🌐 Opening in browser: {abs_path}")
print("\nCountries without box value:", no_box_countries)
