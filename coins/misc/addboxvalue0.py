from flask import Flask, request, jsonify
import json, os

app = Flask(__name__)

COUNTRIES_FILE = "./static/countries.json"
COINS_FILE = "./images/coins.json"


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []
    return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@app.route("/")
def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Country Box Manager</title>
<style>
  body { font-family: Arial, sans-serif; margin: 20px; }
  h1 { color: #333; }
  h2 { margin-top: 30px; color: #555; }
  .table { display: flex; flex-direction: column; width: 90%; border: 1px solid #ccc; margin-bottom: 20px; }
  .row { display: flex; }
  .header { background: #f0f0f0; font-weight: bold; }
  .cell { flex: 1; padding: 8px; border-bottom: 1px solid #ccc; border-right: 1px solid #ccc; }
  .cell:last-child { border-right: none; }
  .row:last-child .cell { border-bottom: none; }
  input[type='number'] { width: 80px; }
  button { padding: 6px 12px; margin-left: 8px; }
  #message { margin-top: 15px; color: green; font-weight: bold; }
  .highlight { background-color: #d8f5d3; } /* both */
  .countries-only { background-color: #fff3cd; } /* only in countries.json */
  .coins-only { background-color: #e2e3e5; } /* only in coins.json */
</style>
</head>
<body>
  <h1>Country & Box Assignment</h1>
  <div class="table" id="countryTable">
    <div class="row header">
      <div class="cell">Country</div>
      <div class="cell">Box</div>
      <div class="cell">Action</div>
      <div class="cell">Exists</div>
    </div>
  </div>

  <p id="message"></p>

  <h2>Extra Countries (in coins.json but not in countries.json)</h2>
  <div class="table" id="extraTable">
    <div class="row header">
      <div class="cell">Country</div>
      <div class="cell">Box</div>
    </div>
  </div>

<script>
async function loadData() {
  const res = await fetch('/data');
  const result = await res.json();
  const countries = result.countries;
  const extras = result.extras;

  const table = document.getElementById("countryTable");
  const extraTable = document.getElementById("extraTable");

  // reset tables
  table.innerHTML = `
    <div class="row header">
      <div class="cell">Country</div>
      <div class="cell">Box</div>
      <div class="cell">Action</div>
      <div class="cell">Exists</div>
    </div>
  `;
  extraTable.innerHTML = `
    <div class="row header">
      <div class="cell">Country</div>
      <div class="cell">Box</div>
    </div>
  `;

  let existsCounter = 1;

  countries.forEach(c => {
    const row = document.createElement("div");
    row.classList.add("row");

    if (c.source === "both") row.classList.add("highlight");
    else if (c.source === "countries") row.classList.add("countries-only");
    else if (c.source === "coins") row.classList.add("coins-only");

    let existsCell = "";
    if (c.source === "both") {
      existsCell = existsCounter++;
    }

    row.innerHTML = `
      <div class="cell">${c.country}</div>
      <div class="cell"><input type="number" value="${c.box || ''}" id="box-${c.country.replace(/\\s+/g,'_')}"></div>
      <div class="cell"><button onclick="saveBox('${c.country.replace(/\\s+/g,'_')}')">Save</button></div>
      <div class="cell">${existsCell}</div>
    `;
    table.appendChild(row);
  });

  extras.forEach(e => {
    const row = document.createElement("div");
    row.classList.add("row", "coins-only");
    row.innerHTML = `
      <div class="cell">${e.country}</div>
      <div class="cell">${e.box || ''}</div>
    `;
    extraTable.appendChild(row);
  });
}

async function saveBox(countryId) {
  const input = document.getElementById("box-" + countryId);
  const boxValue = input.value;
  const countryName = countryId.replace(/_/g,' ');

  if (!boxValue) {
    document.getElementById("message").textContent = "Please enter a box value.";
    return;
  }

  const res = await fetch('/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ country: countryName, box: boxValue })
  });

  const msg = await res.json();
  document.getElementById("message").textContent = msg.status;
  loadData();
}

loadData();
</script>
</body>
</html>
    """


@app.route("/data")
def get_data():
    countries = load_json(COUNTRIES_FILE)
    coins = load_json(COINS_FILE)

    country_names = {c["name"] for c in countries}
    coin_names = {c["country"] for c in coins}
    all_names = country_names.union(coin_names)

    result = []
    for name in sorted(all_names):
        matches = [c for c in coins if c.get("country") == name]
        if matches:
            box_value = matches[0].get("box", "")
        else:
            box_value = ""

        if name in country_names and name in coin_names:
            source = "both"
        elif name in country_names:
            source = "countries"
        else:
            source = "coins"

        result.append({"country": name, "box": box_value, "source": source})

    # Extras: only in coins.json but not in countries.json
    extras = [
        {"country": c.get("country"), "box": c.get("box", "")}
        for c in coins if c.get("country") not in country_names
    ]

    return jsonify({"countries": result, "extras": extras})


@app.route("/update", methods=["POST"])
def update_data():
    data = request.get_json()
    country = data.get("country")
    box = str(data.get("box"))

    coins = load_json(COINS_FILE)

    updated = False
    for entry in coins:
        if entry.get("country") == country:
            entry.setdefault("currency_type", "")
            entry.setdefault("donor_name", "")
            entry.setdefault("image", "")
            entry.setdefault("note", "")
            entry.setdefault("size", "")
            entry.setdefault("year", "")
            entry["box"] = box
            entry.setdefault("hidden_note", "")
            updated = True

    if not updated:
        new_entry = {
            "country": country,
            "currency_type": "",
            "donor_name": "",
            "image": "",
            "note": "",
            "size": "",
            "year": "",
            "box": box,
            "hidden_note": ""
        }
        coins.append(new_entry)

    save_json(COINS_FILE, coins)
    return jsonify({"status": f"Updated box for {country} → {box}"})


if __name__ == "__main__":
    app.run(debug=True)
