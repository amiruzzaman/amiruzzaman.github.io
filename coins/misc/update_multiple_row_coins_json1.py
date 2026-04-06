#!/usr/bin/env python3

from flask import Flask, render_template_string, request, jsonify
import json
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = os.path.join(BASE_DIR, 'images', 'coins.json')

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
<title>Numismatic Vault</title>
<style>
body { font-family: Arial; padding:20px; background:#f5f5f5; }
table { border-collapse: collapse; width:100%; background:white; }
td, th { padding:8px; border:1px solid #ddd; }
tr:hover { background:#f0f0ff; }
input { padding:6px; margin:4px; }
button { padding:6px 12px; margin:4px; cursor:pointer; }
.selected-row { background: #dbeafe !important; }

.instructions {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 20px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}

.instructions h3 {
    margin-bottom: 12px;
    font-size: 18px;
}

.step {
    display: flex;
    align-items: flex-start;
    margin-bottom: 10px;
    gap: 10px;
}

.step-num {
    background: #4f46e5;
    color: white;
    font-weight: bold;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    flex-shrink: 0;
}

.note {
    margin-top: 12px;
    padding: 10px;
    background: #fff7ed;
    border-left: 4px solid #f59e0b;
    font-size: 13px;
}
</style>
</head>

<body>

<h2>🏛️ Numismatic Vault</h2>

<div class="instructions">
    <h3>📘 How to Use This Tool</h3>

    <div class="step">
        <span class="step-num">1</span>
        <div>
            <strong>Search (optional)</strong><br>
            Use the search box to filter coins by country, note, donor, year, etc.
        </div>
    </div>

    <div class="step">
        <span class="step-num">2</span>
        <div>
            <strong>Select rows</strong><br>
            Check the boxes for the rows you want to update.
        </div>
    </div>

    <div class="step">
        <span class="step-num">3</span>
        <div>
            <strong>Bulk update</strong><br>
            Choose a field (e.g., donor name), enter a new value, and click <em>Apply Bulk</em>.
        </div>
    </div>

    <div class="step">
        <span class="step-num">4</span>
        <div>
            <strong>Inline edit (optional)</strong><br>
            Click any cell to edit a single value directly.
        </div>
    </div>

    <div class="step">
        <span class="step-num">5</span>
        <div>
            <strong>Save changes</strong><br>
            Click <em>💾 Save</em> to permanently write changes to the file.
        </div>
    </div>

    <div class="note">
        ⚠️ Changes are not saved automatically. Always click <strong>Save</strong> after making updates.
    </div>
</div>

<input id="searchInput" placeholder="Search...">
<button onclick="saveData()">💾 Save</button>

<br><br>

<select id="bulkField">
    <option value="note">Note</option>
    <option value="donor_name">Donor</option>
    <option value="year">Year</option>
    <option value="country">Country</option>
</select>

<input id="bulkValue" placeholder="New value">
<button onclick="applyBulk()">Apply Bulk</button>

<p id="selectedCount">0 selected</p>

<table>
<thead>
<tr>
<th>Select</th>
<th>Box</th>
<th>Country</th>
<th>Type</th>
<th>Note</th>
<th>Year</th>
<th>Donor</th>
</tr>
</thead>
<tbody id="tableBody"></tbody>
</table>

<script>
let masterData = [];
let selected = new Set();
let searchTerm = "";

// Load data
async function loadData() {
    const res = await fetch('/api/coins');
    masterData = await res.json();
    render();
}

// Filter
function filterData() {
    if (!searchTerm) return masterData;

    return masterData.filter(item =>
        Object.values(item).some(v =>
            String(v || "").toLowerCase().includes(searchTerm.toLowerCase())
        )
    );
}

// Render
function render() {

    // keep valid selections only
    selected = new Set(
        Array.from(selected).filter(id =>
            masterData.some(item => item.image === id)
        )
    );

    const data = filterData();
    let html = "";

    for (let item of data) {
        const id = item.image;
        const isChecked = selected.has(id);

        html += `
        <tr class="${isChecked ? 'selected-row' : ''}">
            <td><input type="checkbox" data-id="${id}" ${isChecked ? "checked":""}></td>
            <td class="edit" data-id="${id}" data-field="box">${item.box || ""}</td>
            <td class="edit" data-id="${id}" data-field="country">${item.country || ""}</td>
            <td class="edit" data-id="${id}" data-field="currency_type">${item.currency_type || ""}</td>
            <td class="edit" data-id="${id}" data-field="note">${item.note || ""}</td>
            <td class="edit" data-id="${id}" data-field="year">${item.year || ""}</td>
            <td class="edit" data-id="${id}" data-field="donor_name">${item.donor_name || ""}</td>
        </tr>`;
    }

    document.getElementById("tableBody").innerHTML = html;

    document.getElementById("selectedCount").innerText =
        selected.size + " selected";

    // checkbox events
    document.querySelectorAll("input[type=checkbox]").forEach(cb => {
        const id = cb.getAttribute("data-id");

        cb.checked = selected.has(id);

        cb.onchange = () => {
            if (cb.checked) selected.add(id);
            else selected.delete(id);

            console.log("Selected:", Array.from(selected));
            render();
        };
    });

    // inline edit (FIXED)
    document.querySelectorAll(".edit").forEach(cell => {
        cell.onclick = () => {
            const id = cell.getAttribute("data-id");
            const field = cell.getAttribute("data-field");

            const item = masterData.find(i => i.image === id);
            const oldVal = item[field] || "";

            const input = document.createElement("input");
            input.value = oldVal;

            cell.innerHTML = "";
            cell.appendChild(input);
            input.focus();

            input.onblur = () => {
                const newVal = input.value;

                for (let i = 0; i < masterData.length; i++) {
                    if (masterData[i].image === id) {
                        masterData[i][field] = newVal;
                        break;
                    }
                }

                render();
            };
        };
    });
}

// BULK UPDATE (FIXED)
function applyBulk() {
    const field = document.getElementById("bulkField").value;
    const value = document.getElementById("bulkValue").value;

    let count = 0;

    for (let i = 0; i < masterData.length; i++) {
        if (selected.has(masterData[i].image)) {
            masterData[i][field] = value;
            count++;
        }
    }

    console.log("After bulk:", masterData);

    alert("Updated " + count + " rows");
    render();
}

// SAVE (DEBUG INCLUDED)
async function saveData() {
    console.log("DATA BEING SENT:", JSON.stringify(masterData, null, 2));

    await fetch('/api/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(masterData)
    });

    alert("Saved!");
}

// Search
document.getElementById("searchInput").addEventListener("input", e => {
    searchTerm = e.target.value;
    render();
});

loadData();
</script>

</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/coins')
def get_coins():
    try:
        with open(FILE_NAME, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        print("ERROR:", e)
        return jsonify([])

@app.route('/api/save', methods=['POST'])
def save_coins():
    try:
        data = request.json

        print("==== SAMPLE RECEIVED ====")
        print(data[0])
        print("TOTAL:", len(data))

        with open(FILE_NAME, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print("✅ SAVED")

        return jsonify({'status':'ok'})
    except Exception as e:
        print("SAVE ERROR:", e)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)