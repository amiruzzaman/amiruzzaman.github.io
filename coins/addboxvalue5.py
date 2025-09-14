from flask import Flask, request, jsonify, send_file
import json, os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io

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
  .tabs { margin-bottom: 15px; }
  .tab-btn { padding: 8px 16px; cursor: pointer; border: 1px solid #ccc; background: #eee; }
  .tab-btn.active { background: #ddd; font-weight: bold; }
  .tab-content { display: none; }
  .tab-content.active { display: block; }
  .table { display: flex; flex-direction: column; width: 95%; border: 1px solid #ccc; margin-bottom: 20px; }
  .row { display: flex; }
  .header { background: #f0f0f0; font-weight: bold; }
  .cell { flex: 1; padding: 8px; border-bottom: 1px solid #ccc; border-right: 1px solid #ccc; }
  .cell:last-child { border-right: none; }
  .row:last-child .cell { border-bottom: none; }
  input[type='number'] { width: 80px; }
  button { padding: 6px 12px; margin-left: 8px; }
  .highlight { background-color: #d8f5d3; } /* both */
  .countries-only { background-color: #fff3cd; }
  .coins-only { background-color: #e2e3e5; }
  .alpha-header { background: #ddd; font-weight: bold; padding: 6px; }
  .search-sort { margin-bottom: 10px; }
  
  /* Message bar styles */
  #messageBar {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    padding: 15px;
    text-align: center;
    font-weight: bold;
    z-index: 1000;
    opacity: 0.9;
    display: none;
    color: white;
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
  }
  
  .success { background-color: #4CAF50; } /* Green */
  .error { background-color: #F44336; } /* Red */
  
  /* Editable cell styles */
  .editable-cell {
    cursor: pointer;
    min-height: 20px;
  }
  
  .editable-cell input {
    width: 80px;
    padding: 4px;
  }
</style>
</head>
<body>
  <div id="messageBar"></div>
  <h1>Country & Box Manager</h1>

  <div class="tabs">
    <button class="tab-btn active" onclick="showTab('manageTab')">Manage Boxes</button>
    <button class="tab-btn" onclick="showTab('listTab')">Country List</button>
  </div>

  <!-- Manage tab -->
  <div id="manageTab" class="tab-content active">
    <div class="table" id="countryTable">
      <div class="row header">
        <div class="cell">Country</div>
        <div class="cell">Box</div>
        <div class="cell">Exists</div>
      </div>
    </div>
    <h2>Extra Countries (in coins.json but not in countries.json)</h2>
    <div class="table" id="extraTable">
      <div class="row header">
        <div class="cell">Country</div>
        <div class="cell">Box</div>
      </div>
    </div>
    <!-- Add this button in the Manage tab section, after the tables -->
<button onclick="exportPDF()" style="margin-top: 20px; padding: 10px 15px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;">
    Export to PDF
</button>
  </div>

  <!-- Country list tab -->
  <div id="listTab" class="tab-content">
    <div class="search-sort">
      <input type="text" id="searchBox" placeholder="Search country...">
      <button onclick="sortList('name')">Sort by Name</button>
      <button onclick="sortList('box')">Sort by Box</button>
      <button onclick="toggleOrder()">Toggle Asc/Desc</button>
    </div>
    <div id="countryList"></div>
  </div>

<script>
let coinCountries = [];
let sortField = "name";
let sortAsc = true;
let originalValues = {};

function showTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(tab => tab.classList.remove("active"));
  if (tabId === "manageTab") {
    document.querySelector(".tab-btn:nth-child(1)").classList.add("active");
  } else {
    document.querySelector(".tab-btn:nth-child(2)").classList.add("active");
    renderList();
  }
  document.getElementById(tabId).classList.add("active");
}

function showMessage(message, isSuccess) {
  const messageBar = document.getElementById("messageBar");
  messageBar.textContent = message;
  messageBar.className = isSuccess ? "success" : "error";
  messageBar.style.display = "block";
  
  setTimeout(() => {
    messageBar.style.display = "none";
  }, 3000);
}

function makeCellEditable(cell, country, currentValue, source) {
  // Store original value
  originalValues[country] = {
    value: currentValue || "",
    source: source
  };
  
  const input = document.createElement("input");
  input.type = "number";
  input.value = currentValue || "";
  input.style.width = "80%";
  
  // Replace cell content with input
  cell.innerHTML = "";
  cell.appendChild(input);
  input.focus();
  
  // Save on blur
  input.addEventListener("blur", () => {
    const newValue = input.value.trim();
    // Only save if value has changed and is not empty, and country exists in coins.json
    if (newValue !== originalValues[country].value && newValue !== "" && originalValues[country].source !== "countries") {
      saveBox(country, newValue);
    } else {
      // Restore original value
      cell.textContent = originalValues[country].value || "";
    }
    delete originalValues[country];
  });
  
  // Also save on Enter key
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      input.blur();
    }
  });
  
  // Cancel on Escape key
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      cell.textContent = originalValues[country].value || "";
      delete originalValues[country];
    }
  });
}

async function loadData() {
  const res = await fetch('/data');
  const result = await res.json();
  const countries = result.countries;
  const extras = result.extras;
  coinCountries = result.coinCountries; // only from coins.json

  const table = document.getElementById("countryTable");
  const extraTable = document.getElementById("extraTable");

  // reset tables
  table.innerHTML = `
    <div class="row header">
      <div class="cell">Country</div>
      <div class="cell">Box</div>
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
    if (c.source === "both") existsCell = existsCounter++;

    row.innerHTML = `
      <div class="cell">${c.country}</div>
      <div class="cell editable-cell" data-country="${c.country}" data-source="${c.source}">${c.box || ''}</div>
      <div class="cell">${existsCell}</div>
    `;
    table.appendChild(row);
  });

  // Add click event to editable cells
  document.querySelectorAll('.editable-cell').forEach(cell => {
    cell.addEventListener('click', () => {
      const country = cell.getAttribute('data-country');
      const source = cell.getAttribute('data-source');
      const currentValue = cell.textContent;
      makeCellEditable(cell, country, currentValue, source);
    });
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

// normalize country name for sorting (ignore "The ")
function normalizeName(name) {
  return name.replace(/^The\\s+/i, "").toLowerCase();
}

function sortList(field) {
  sortField = field;
  renderList();
}

function toggleOrder() {
  sortAsc = !sortAsc;
  renderList();
}

function renderList() {
  const query = document.getElementById("searchBox").value.toLowerCase();
  let filtered = coinCountries.filter(c => c.country.toLowerCase().includes(query));

  filtered.sort((a, b) => {
    if (sortField === "name") {
      let an = normalizeName(a.country);
      let bn = normalizeName(b.country);
      if (an < bn) return sortAsc ? -1 : 1;
      if (an > bn) return sortAsc ? 1 : -1;
      return 0;
    } else {
      let ab = parseInt(a.box || 0);
      let bb = parseInt(b.box || 0);
      if (ab < bb) return sortAsc ? -1 : 1;
      if (ab > bb) return sortAsc ? 1 : -1;
      return 0;
    }
  });

  const container = document.getElementById("countryList");
  container.innerHTML = "";

  let currentLetter = "";
  filtered.forEach(c => {
    let firstLetter = normalizeName(c.country).charAt(0).toUpperCase();
    if (firstLetter !== currentLetter) {
      currentLetter = firstLetter;
      const header = document.createElement("div");
      header.classList.add("alpha-header");
      header.textContent = currentLetter;
      container.appendChild(header);
    }
    const row = document.createElement("div");
    row.classList.add("row");
    row.innerHTML = `
      <div class="cell">${c.country}</div>
      <div class="cell">${c.box || ''}</div>
    `;
    container.appendChild(row);
  });
}

async function saveBox(countryName, boxValue) {
  try {
    const res = await fetch('/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ country: countryName, box: boxValue })
    });

    if (!res.ok) {
      throw new Error(`Server returned ${res.status}: ${res.statusText}`);
    }

    const msg = await res.json();
    showMessage(msg.status, true);
    loadData(); // Reload data to refresh the display
  } catch (error) {
    showMessage("Error saving data: " + error.message, false);
    // Reload data to restore original state
    loadData();
  }
}

document.getElementById("searchBox").addEventListener("input", renderList);

// function to handle the export
function exportPDF() {
    window.open('/export-pdf', '_blank');
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
            box_value = matches[0].get("box", "")  # take first match
        else:
            box_value = ""

        if name in country_names and name in coin_names:
            source = "both"
        elif name in country_names:
            source = "countries"
        else:
            source = "coins"

        result.append({"country": name, "box": box_value, "source": source})

    extras = [
        {"country": c.get("country"), "box": c.get("box", "")}
        for c in coins if c.get("country") not in country_names
    ]

    # Deduplicate coinCountries
    seen = {}
    for c in coins:
        country = c.get("country")
        if country not in seen:   # only keep first occurrence
            seen[country] = {"country": country, "box": c.get("box", "")}

    coinCountries = list(seen.values())

    return jsonify({"countries": result, "extras": extras, "coinCountries": coinCountries})


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
        # Only create new entry if country exists in coins.json
        # This prevents creating entries for countries that only exist in countries.json
        pass

    save_json(COINS_FILE, coins)
    return jsonify({"status": f"Updated box for {country} → {box}"})


# @app.route("/export-pdf")
# def export_pdf():
#     # Get the data
#     countries = load_json(COUNTRIES_FILE)
#     coins = load_json(COINS_FILE)
    
#     # Create a file-like buffer to receive PDF data
#     buffer = io.BytesIO()
    
#     # Create the PDF object, using the buffer as its "file"
#     doc = SimpleDocTemplate(buffer, pagesize=letter)
    
#     # Container for the 'Flowable' objects
#     elements = []
#     styles = getSampleStyleSheet()
    
#     # Add title
#     title = Paragraph("Country Box Manager Export", styles['Title'])
#     elements.append(title)
    
#     # Prepare data for the table
#     country_names = {c["name"] for c in countries}
#     coin_names = {c["country"] for c in coins}
#     all_names = country_names.union(coin_names)
    
#     result = []
#     for name in sorted(all_names):
#         matches = [c for c in coins if c.get("country") == name]
#         if matches:
#             box_value = matches[0].get("box", "")  # take first match
#         else:
#             box_value = ""

#         if name in country_names and name in coin_names:
#             source = "both"
#         elif name in country_names:
#             source = "countries"
#         else:
#             source = "coins"

#         result.append({"country": name, "box": box_value, "source": source})
    
#     # Organize data into 4 columns
#     #table_data = [["Country", "Box", "Country", "Box", "Country", "Box", "Country", "Box"]]
    

#     # Calculate how many rows we need (ceil division)
#     #num_rows = (len(result) + 3) // 4

#     table_data = [["Country", "Box", "Country", "Box", "Country", "Box"]]
    
#     # Calculate how many rows we need (ceil division)
#     num_rows = (len(result) + 3) // 3
    
#     for i in range(num_rows):
#         row = []
#         for j in range(3): #4
#             idx = i + j * num_rows
#             if idx < len(result):
#                 country_data = result[idx]
#                 row.extend([country_data["country"], str(country_data["box"])])
#             else:
#                 row.extend(["", ""])
#         table_data.append(row)
    
#     # Create table
#     table = Table(table_data)
    
#     # Add style to table
#     style = TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTSIZE', (0, 0), (-1, 0), 10),
#         ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
#         ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
#         ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
#         ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
#         ('FONTSIZE', (0, 1), (-1, -1), 8),
#         ('GRID', (0, 0), (-1, -1), 1, colors.black)
#     ])
    
#     # Alternate row colors for better readability
#     for i in range(1, len(table_data)):
#         if i % 2 == 0:
#             bg_color = colors.lightgrey
#         else:
#             bg_color = colors.beige
#         style.add('BACKGROUND', (0, i), (-1, i), bg_color)
    
#     table.setStyle(style)
    
#     # Add table to elements
#     elements.append(table)
    
#     # Build PDF
#     doc.build(elements)
    
#     # File response
#     buffer.seek(0)
#     return send_file(
#         buffer,
#         as_attachment=True,
#         download_name="country_box_export.pdf",
#         mimetype="application/pdf"
#     )

@app.route("/export-pdf")
def export_pdf():
    # Get the data
    countries = load_json(COUNTRIES_FILE)
    coins = load_json(COINS_FILE)
    
    # Create a file-like buffer to receive PDF data
    buffer = io.BytesIO()
    
    # Create the PDF object, using the buffer as its "file"
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    # Container for the 'Flowable' objects
    elements = []
    styles = getSampleStyleSheet()
    
    # Add title
    title = Paragraph("Country Box Manager Export", styles['Title'])
    elements.append(title)
    
    # Prepare data for the table
    country_names = {c["name"] for c in countries}
    coin_names = {c["country"] for c in coins}
    all_names = country_names.union(coin_names)
    
    result = []
    for name in sorted(all_names):
        matches = [c for c in coins if c.get("country") == name]
        if matches:
            box_value = matches[0].get("box", "")  # take first match
        else:
            box_value = ""

        if name in country_names and name in coin_names:
            source = "both"
        elif name in country_names:
            source = "countries"
        else:
            source = "coins"

        result.append({"country": name, "box": box_value, "source": source})
    
    # Organize data into 3 columns (each column has Country and Box)
    table_data = [["Country", "Box", "Country", "Box", "Country", "Box"]]
    
    # Calculate how many rows we need (ceil division)
    num_rows = (len(result) + 2) // 3
    
    for i in range(num_rows):
        row = []
        for j in range(3):
            idx = i + j * num_rows
            if idx < len(result):
                country_data = result[idx]
                row.extend([country_data["country"], str(country_data["box"])])
            else:
                row.extend(["", ""])
        table_data.append(row)
    
    # Create table
    table = Table(table_data)
    
    # Add style to table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Header row centered
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    
    # Set alignment for data rows - country names left, box numbers centered
    for i in range(1, len(table_data)):
        # Align country names to left (odd-numbered columns: 0, 2, 4)
        style.add('ALIGN', (0, i), (0, i), 'LEFT')
        style.add('ALIGN', (2, i), (2, i), 'LEFT')
        style.add('ALIGN', (4, i), (4, i), 'LEFT')
        
        # Align box numbers to center (even-numbered columns: 1, 3, 5)
        style.add('ALIGN', (1, i), (1, i), 'CENTER')
        style.add('ALIGN', (3, i), (3, i), 'CENTER')
        style.add('ALIGN', (5, i), (5, i), 'CENTER')
    
    # Alternate row colors for better readability
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            bg_color = colors.lightgrey
        else:
            bg_color = colors.beige
        style.add('BACKGROUND', (0, i), (-1, i), bg_color)
    
    table.setStyle(style)
    
    # Add table to elements
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    
    # File response
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="country_box_export.pdf",
        mimetype="application/pdf"
    )


if __name__ == "__main__":
    app.run(debug=True)