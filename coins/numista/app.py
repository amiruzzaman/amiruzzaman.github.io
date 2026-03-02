import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template_string, request, jsonify
import re

app = Flask(__name__)

# --- UI: GRID LAYOUT & HD IMAGE SUPPORT ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Numista HD Collector</title>
    <style>
        :root { --primary: #2c3e50; --accent: #27ae60; --bg: #f4f7f6; }
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: var(--bg); padding: 40px; margin: 0; }
        .container { max-width: 1000px; margin: auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
        
        .search-area { display: flex; gap: 10px; margin-bottom: 30px; }
        input { flex: 1; padding: 15px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; outline: none; }
        input:focus { border-color: var(--accent); }
        button { padding: 15px 30px; background: var(--accent); color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
        
        #results { display: none; }
        .coin-title { text-align: center; color: var(--primary); font-size: 2.2em; border-bottom: 3px solid var(--accent); padding-bottom: 10px; margin-bottom: 25px; }
        
        /* High-Res Gallery */
        .img-gallery { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        .img-box { text-align: center; background: #fff; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
        .img-box img { width: 100%; max-height: 400px; object-fit: contain; border-radius: 5px; cursor: pointer; }
        .download-btn { display: inline-block; margin-top: 10px; color: var(--accent); text-decoration: none; font-weight: bold; border: 1px solid var(--accent); padding: 5px 12px; border-radius: 4px; }

        /* Formatted Specification Grid */
        .spec-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }
        .spec-card { background: #fafafa; padding: 15px; border-radius: 8px; border-left: 5px solid var(--accent); }
        .spec-label { font-size: 0.75em; color: #95a5a6; text-transform: uppercase; font-weight: bold; }
        .spec-value { font-size: 1.1em; color: var(--primary); margin-top: 5px; line-height: 1.4; }

        #status { color: #e67e22; text-align: center; font-weight: bold; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h2 style="text-align: center; color: var(--primary);">Numista HD Extractor</h2>
        <div class="search-area">
            <input type="text" id="url" value="https://en.numista.com/catalogue/pieces210867.html">
            <button onclick="fetchData()">Extract HD Data</button>
        </div>
        <p id="status"></p>

        <div id="results">
            <h1 id="title" class="coin-title"></h1>
            <div class="img-gallery">
                <div class="img-box">
                    <img id="imgObv" src="">
                    <a id="dlObv" class="download-btn" target="_blank">View HD Obverse</a>
                </div>
                <div class="img-box">
                    <img id="imgRev" src="">
                    <a id="dlRev" class="download-btn" target="_blank">View HD Reverse</a>
                </div>
            </div>
            <div id="specGrid" class="spec-grid"></div>
        </div>
    </div>

    <script>
        async function fetchData() {
            const status = document.getElementById('status');
            const results = document.getElementById('results');
            status.innerText = "🔍 Accessing Numista and formatting HD data...";
            results.style.display = "none";

            try {
                const res = await fetch('/scrape', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ url: document.getElementById('url').value })
                });
                const data = await res.json();

                if(data.error) {
                    status.innerText = "❌ " + data.error;
                } else {
                    status.innerText = "";
                    results.style.display = "block";
                    document.getElementById('title').innerText = data.title;
                    
                    document.getElementById('imgObv').src = data.images[0] || '';
                    document.getElementById('dlObv').href = data.images[0] || '';
                    document.getElementById('imgRev').src = data.images[1] || '';
                    document.getElementById('dlRev').href = data.images[1] || '';

                    const grid = document.getElementById('specGrid');
                    grid.innerHTML = "";
                    for (const [k, v] of Object.entries(data.info)) {
                        grid.innerHTML += `
                            <div class="spec-card">
                                <div class="spec-label">${k}</div>
                                <div class="spec-value">${v}</div>
                            </div>`;
                    }
                }
            } catch (e) {
                status.innerText = "❌ Connection failed.";
            }
        }
    </script>
</body>
</html>
"""

# --- BACKEND LOGIC ---
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/scrape', methods=['POST'])
def scrape():
    target_url = request.json.get('url')
    # Mimic app1.py headers for better access
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    try:
        response = requests.get(target_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return jsonify({"error": f"Numista Access Denied (Code {response.status_code})"}), 403

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Target the Coin Title
        title = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Unknown Coin"

        # 2. Extract HD Images
        # Target 'magni_foc' links and convert thumbnails to HD originals
        hd_images = []
        gallery = soup.find('div', class_='coingallery')
        if gallery:
            for a in gallery.find_all('a', class_='magni_foc'):
                img_tag = a.find('img')
                if img_tag:
                    # Conversion logic: ..._th.jpg -> .jpg
                    hd_url = img_tag['src'].replace('_th.jpg', '.jpg')
                    if not hd_url.startswith('http'):
                        hd_url = "https://en.numista.com" + hd_url
                    hd_images.append(hd_url)

        # 3. Format Specific Specifications
        # Targeted table extraction instead of general text dump
        info_data = {}
        specs_table = soup.find('table', id='fiche_caracteristiques')
        if specs_table:
            for row in specs_table.find_all('tr'):
                cols = row.find_all(['th', 'td'])
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True)
                    # Clean the value to remove messy tabs and line breaks
                    val = " ".join(cols[1].get_text().split())
                    info_data[key] = val

        return jsonify({
            "title": title,
            "images": hd_images[:2] if len(hd_images) >= 2 else ["", ""],
            "info": info_data
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)