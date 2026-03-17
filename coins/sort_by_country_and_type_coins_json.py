from flask import Flask, jsonify, render_template_string
from collections import defaultdict
import json
import os

app = Flask(__name__)

JSON_FILE = "images/coins.json"


# -------------------------
# LOAD DATA
# -------------------------
def load_data():
    if not os.path.exists(JSON_FILE):
        return []

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------
# PROCESS DATA
# -------------------------
def process_data():

    data = load_data()

    grouped = defaultdict(list)

    for obj in data:
        country = obj.get("country", "Unknown")
        grouped[country].append(obj)

    processed = []

    for country, items in grouped.items():

        # find box value
        box_value = None
        for i in items:
            if i.get("box"):
                box_value = i["box"]
                break

        # copy box value
        if box_value:
            for i in items:
                i["box"] = box_value

        # sort by currency_type
        items = sorted(items, key=lambda x: x.get("currency_type", ""))

        processed.extend(items)

    # save updated JSON
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2)

    return processed


# -------------------------
# ROUTES
# -------------------------
@app.route("/data")
def data():
    return jsonify(load_data())


@app.route("/process")
def process():
    return jsonify(process_data())


# -------------------------
# PAGE
# -------------------------
@app.route("/")
def home():

    page = """

<!DOCTYPE html>
<html>

<head>

<title>Coin Manager</title>

<style>

body{
    font-family:Arial;
    background:#f2f2f2;
    padding:40px;
}

h1{
    margin-bottom:20px;
}

button{
    padding:10px 18px;
    font-size:16px;
    margin-bottom:20px;
    cursor:pointer;
}

.table{
    display:flex;
    flex-direction:column;
    background:white;
    border-radius:6px;
    overflow:hidden;
}

.row{
    display:flex;
    padding:10px;
    border-bottom:1px solid #ddd;
}

.header{
    background:#444;
    color:white;
    font-weight:bold;
}

.cell{
    flex:1;
}

.country{
    background:#e8f2ff;
}

</style>

</head>

<body>

<h1>Coins JSON Viewer</h1>

<button onclick="processData()">Process & Save</button>

<div id="table" class="table"></div>

<script>

async function loadData(){

    let res = await fetch('/data')
    let data = await res.json()

    let table = document.getElementById("table")

    table.innerHTML = ""

    let header = document.createElement("div")
    header.className = "row header"

    header.innerHTML =
        "<div class='cell'>Country</div>" +
        "<div class='cell'>Currency Type</div>" +
        "<div class='cell'>Year</div>" +
        "<div class='cell'>Box</div>"

    table.appendChild(header)

    data.forEach(item=>{

        let row = document.createElement("div")
        row.className="row"

        row.innerHTML =
            "<div class='cell country'>" + (item.country || "") + "</div>" +
            "<div class='cell'>" + (item.currency_type || "") + "</div>" +
            "<div class='cell'>" + (item.year || "") + "</div>" +
            "<div class='cell'>" + (item.box || "") + "</div>"

        table.appendChild(row)

    })

}


async function processData(){

    await fetch('/process')

    loadData()

}

loadData()

</script>

</body>

</html>

"""

    return render_template_string(page)


# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)