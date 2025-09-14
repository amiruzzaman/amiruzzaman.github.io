from flask import Flask, request, jsonify, send_file
import json
import os

app = Flask(__name__)

COUNTRIES_FILE = "list_of_countries_fixed.json"
SAVED_FILE = "saved_data.json"

# Serve single-page app
@app.route("/")
def index():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Country Box Selector</title>
<style>
  body { font-family: Arial, sans-serif; margin: 20px; }
  h1 { color: #333; }
  label { display: block; margin-top: 10px; }
  select, input, button {
    margin-top: 5px;
    padding: 8px;
    width: 250px;
  }
  #message { margin-top: 15px; color: green; }
</style>
</head>
<body>
  <h1>Country & Box Assignment</h1>

  <label for="country">Select Country:</label>
  <select id="country"></select>

  <label for="box">Enter Box Number:</label>
  <input type="number" id="box" placeholder="e.g., 1" />

  <button onclick="saveData()">Save</button>

  <p id="message"></p>

<script>
async function loadCountries() {
  const res = await fetch('/countries');
  const data = await res.json();
  const dropdown = document.getElementById('country');
  data.forEach(c => {
    let option = document.createElement('option');
    option.value = c.name;
    option.textContent = c.name;
    dropdown.appendChild(option);
  });
}

async function saveData() {
  const country = document.getElementById('country').value;
  const box = document.getElementById('box').value;

  if (!country || !box) {
    document.getElementById('message').textContent = "Please select country and enter box.";
    return;
  }

  const payload = { country, box };

  const res = await fetch('/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  const msg = await res.json();
  document.getElementById('message').textContent = msg.status;
}

loadCountries();
</script>
</body>
</html>
    """

# API: Load country list
@app.route("/countries")
def get_countries():
    with open(COUNTRIES_FILE, "r", encoding="utf-8") as f:
        countries = json.load(f)
    return jsonify(countries)

# API: Save user input
@app.route("/save", methods=["POST"])
def save():
    data = request.get_json()
    country = data.get("country")
    box = str(data.get("box"))

    entry = {
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

    # Append to JSON file
    saved = []
    if os.path.exists(SAVED_FILE):
        with open(SAVED_FILE, "r", encoding="utf-8") as f:
            try:
                saved = json.load(f)
            except:
                saved = []

    saved.append(entry)

    with open(SAVED_FILE, "w", encoding="utf-8") as f:
        json.dump(saved, f, indent=2)

    return jsonify({"status": f"Saved {country} in box {box}."})

if __name__ == "__main__":
    app.run(debug=True)
