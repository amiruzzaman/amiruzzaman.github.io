from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import json
import os
from collections import defaultdict
import urllib.parse

app = Flask(__name__)

# Path to the JSON file
JSON_FILE_PATH = 'images/coins.json'

def load_data():
    """Load data from the JSON file"""
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

def save_data(data):
    """Save data to the JSON file"""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(JSON_FILE_PATH), exist_ok=True)
    
    with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def process_coin_data(data):
    """
    Process coin data according to the rules:
    1. For objects with same country, find which have "box" values
    2. Add "box" key and value to common country objects
    3. If country has multiple objects and one doesn't have "image", delete that object
    4. Ensure all objects with same country have same "box" value
    """
    # Group data by country
    country_groups = defaultdict(list)
    
    # First pass: group by country
    for item in data:
        country = item.get('country', 'Unknown')
        country_groups[country].append(item)
    
    processed_data = []
    stats = {
        'total_countries': len(country_groups),
        'total_items_before': len(data),
        'items_removed': 0,
        'boxes_added': 0
    }
    
    # Process each country group
    for country, items in country_groups.items():
        # Find box value for this country (take first non-empty box found)
        box_value = None
        for item in items:
            if item.get('box') and str(item['box']).strip():
                box_value = item['box']
                break
        
        # If country has multiple items, check for images
        if len(items) > 1:
            # Check if any items have images
            has_items_with_images = any(
                item.get('image') and str(item['image']).strip() 
                for item in items
            )
            
            if has_items_with_images:
                # Keep only items with images
                items_to_keep = [
                    item for item in items 
                    if item.get('image') and str(item['image']).strip()
                ]
                stats['items_removed'] += (len(items) - len(items_to_keep))
                items = items_to_keep
        
        # Add box value to all items in this country group
        if box_value:
            for item in items:
                if not item.get('box') or not str(item['box']).strip():
                    item['box'] = box_value
                    stats['boxes_added'] += 1
            # Ensure all items have the same box value
            for item in items:
                item['box'] = box_value
        
        # Add processed items to result
        processed_data.extend(items)
    
    stats['total_items_after'] = len(processed_data)
    return processed_data, stats

def get_image_path(country, image_filename):
    """Get the path to an image file"""
    if not image_filename or not image_filename.strip():
        return None
    
    # Clean the country name for filesystem
    safe_country = "".join(c for c in country if c.isalnum() or c in (' ', '-', '_')).rstrip()
    image_path = os.path.join('images', safe_country, image_filename)
    
    # Check if file exists
    if os.path.exists(image_path):
        return image_path
    return None

@app.route('/')
def index():
    """Main page showing the coin data"""
    data = load_data()
    processed_data, stats = process_coin_data(data)
    
    # Group by country for display
    country_groups = defaultdict(list)
    for item in processed_data:
        country = item.get('country', 'Unknown')
        country_groups[country].append(item)
    
    # Convert to list of tuples for sorting
    country_list = [(country, items) for country, items in country_groups.items()]
    country_list.sort(key=lambda x: x[0])  # Sort by country name
    
    return render_template_string(HTML_TEMPLATE, 
                                countries=country_list,
                                stats=stats,
                                total_countries=len(country_groups),
                                total_items=len(processed_data))

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    """Show detailed view of a specific item"""
    data = load_data()
    
    if item_id < 0 or item_id >= len(data):
        return "Item not found", 404
    
    item = data[item_id]
    country = item.get('country', 'Unknown')
    image_filename = item.get('image')
    
    # Get image path if available
    image_path = None
    if image_filename:
        image_path = get_image_path(country, image_filename)
    
    return render_template_string(DETAIL_TEMPLATE, 
                                item=item, 
                                item_id=item_id,
                                image_path=image_path,
                                total_items=len(data))

@app.route('/images/<path:country>/<path:filename>')
def serve_image(country, filename):
    """Serve image files"""
    safe_country = urllib.parse.unquote(country)
    directory = os.path.join('images', safe_country)
    
    try:
        return send_from_directory(directory, filename)
    except FileNotFoundError:
        return "Image not found", 404

@app.route('/process', methods=['POST'])
def process_data():
    """Process the data and save it back to the file"""
    data = load_data()
    processed_data, stats = process_coin_data(data)
    
    # Save processed data back to file
    save_data(processed_data)
    
    return jsonify({
        'success': True,
        'message': f'Processed {len(processed_data)} items across {stats["total_countries"]} countries',
        'stats': stats
    })

@app.route('/original')
def show_original():
    """Show original unprocessed data"""
    data = load_data()
    
    # Group by country for display
    country_groups = defaultdict(list)
    for item in data:
        country = item.get('country', 'Unknown')
        country_groups[country].append(item)
    
    country_list = [(country, items) for country, items in country_groups.items()]
    country_list.sort(key=lambda x: x[0])
    
    return render_template_string(HTML_TEMPLATE, 
                                countries=country_list,
                                stats={'total_countries': len(country_groups), 'total_items': len(data)},
                                total_countries=len(country_groups),
                                total_items=len(data),
                                show_original=True)

@app.route('/download')
def download_json():
    """Download the processed JSON file"""
    return send_file(JSON_FILE_PATH, as_attachment=True)

@app.route('/api/data')
def api_data():
    """Return raw JSON data"""
    data = load_data()
    return jsonify(data)

@app.route('/api/processed-data')
def api_processed_data():
    """Return processed JSON data"""
    data = load_data()
    processed_data, stats = process_coin_data(data)
    return jsonify(processed_data)

# HTML Template for main page
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coin Collection Data Processor</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        header {
            background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .content {
            padding: 30px;
        }
        
        .controls {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        button {
            background-color: #4a6ee0;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1rem;
            transition: background-color 0.3s;
        }
        
        button:hover {
            background-color: #3a5ecf;
        }
        
        .stats {
            background-color: #f0f4ff;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
        }
        
        .stat-item {
            flex: 1;
            min-width: 150px;
            text-align: center;
            padding: 10px;
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }
        
        .stat-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #4a6ee0;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: #666;
        }
        
        .data-section {
            margin-top: 30px;
        }
        
        .section-title {
            font-size: 1.5rem;
            margin-bottom: 15px;
            color: #4a6ee0;
            border-bottom: 2px solid #f0f4ff;
            padding-bottom: 10px;
        }
        
        .data-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .country-card {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
            padding: 20px;
            transition: transform 0.3s;
        }
        
        .country-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.15);
        }
        
        .country-name {
            font-size: 1.3rem;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }
        
        .country-box {
            display: inline-block;
            background-color: #4a6ee0;
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.9rem;
            margin-bottom: 10px;
        }
        
        .coin-list {
            list-style-type: none;
            margin-top: 10px;
        }
        
        .coin-item {
            padding: 8px 0;
            border-bottom: 1px solid #f0f4ff;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .coin-item:hover {
            background-color: #f8f9ff;
            padding-left: 5px;
            border-radius: 4px;
        }
        
        .coin-type {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.8rem;
            margin-right: 5px;
        }
        
        .coin-coin {
            background-color: #e6f7ff;
            color: #1890ff;
        }
        
        .coin-paper-bill {
            background-color: #f6ffed;
            color: #52c41a;
        }
        
        .coin-antique {
            background-color: #fff7e6;
            color: #fa8c16;
        }
        
        .coin-other {
            background-color: #f9f0ff;
            color: #722ed1;
        }
        
        .no-image {
            color: #ff4d4f;
            font-style: italic;
        }
        
        .processing-info {
            background-color: #fffbe6;
            border-left: 4px solid #faad14;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 5px 5px 0;
        }
        
        .alert {
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
            display: none;
        }
        
        .alert-success {
            background-color: #f6ffed;
            border: 1px solid #b7eb8f;
            color: #52c41a;
        }
        
        .alert-error {
            background-color: #fff2f0;
            border: 1px solid #ffccc7;
            color: #ff4d4f;
        }
        
        @media (max-width: 768px) {
            .controls {
                flex-direction: column;
            }
            
            .data-container {
                grid-template-columns: 1fr;
            }
            
            .stats {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Coin Collection Data Processor</h1>
            <p class="subtitle">Process and manage coin collection data from JSON file</p>
        </header>
        
        <div class="content">
            <div class="controls">
                <button onclick="processData()">Process & Save Data</button>
                <button onclick="showOriginal()">Show Original Data</button>
                <button onclick="showProcessed()">Show Processed Data</button>
                <button onclick="downloadJSON()">Download JSON</button>
            </div>
            
            <div id="alert" class="alert"></div>
            
            <div class="processing-info">
                <h3>Processing Rules:</h3>
                <ul>
                    <li>For objects with the same country value, find which objects have "box" values</li>
                    <li>Add the "box" key and value to all objects with the same country</li>
                    <li>If a country has multiple objects and one doesn't have an "image" value, delete that object</li>
                    <li>Ensure all objects with the same country have the same "box" value</li>
                </ul>
            </div>
            
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-value">{{ total_countries }}</div>
                    <div class="stat-label">Total Countries</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{{ total_items }}</div>
                    <div class="stat-label">Total Items</div>
                </div>
                {% if stats.items_removed is defined %}
                <div class="stat-item">
                    <div class="stat-value">{{ stats.items_removed }}</div>
                    <div class="stat-label">Items Removed</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{{ stats.boxes_added }}</div>
                    <div class="stat-label">Boxes Added</div>
                </div>
                {% endif %}
            </div>
            
            <div class="data-section">
                <h2 class="section-title">
                    {% if show_original %}
                        Original Coin Data
                    {% else %}
                        Processed Coin Data
                    {% endif %}
                </h2>
                <div class="data-container">
                    {% for country, items in countries %}
                    <div class="country-card">
                        <div class="country-name">{{ country }}</div>
                        <div class="country-box">Box: {{ items[0].box if items[0].box else 'No box assigned' }}</div>
                        <ul class="coin-list">
                            {% for item in items %}
                            <li class="coin-item" onclick="viewItemDetail({{ loop.index0 }})">
                                <span class="coin-type {{ 'coin-coin' if item.currency_type == 'coin' else 'coin-paper-bill' if item.currency_type == 'paper-bill' else 'coin-antique' if item.currency_type == 'antique' else 'coin-other' }}">
                                    {{ item.currency_type if item.currency_type else 'Unknown' }}
                                </span>
                                {{ item.year if item.year else 'Unknown year' }} - {{ item.note[:50] + '...' if item.note and item.note|length > 50 else item.note if item.note else 'No description' }}
                                {% if not item.image or not item.image.strip() %}
                                <span class="no-image"> (No image)</span>
                                {% endif %}
                            </li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>

    <script>
        function showAlert(message, type) {
            const alert = document.getElementById('alert');
            alert.textContent = message;
            alert.className = `alert alert-${type}`;
            alert.style.display = 'block';
            setTimeout(() => {
                alert.style.display = 'none';
            }, 5000);
        }

        async function processData() {
            try {
                const response = await fetch('/process', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showAlert(result.message, 'success');
                    // Reload the page to show updated data
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1000);
                } else {
                    showAlert('Error processing data', 'error');
                }
            } catch (error) {
                showAlert('Error: ' + error.message, 'error');
            }
        }

        function showOriginal() {
            window.location.href = '/original';
        }

        function showProcessed() {
            window.location.href = '/';
        }

        function downloadJSON() {
            window.location.href = '/download';
        }

        function viewItemDetail(itemIndex) {
            window.location.href = `/item/${itemIndex}`;
        }
    </script>
</body>
</html>
'''

# HTML Template for item detail page
DETAIL_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coin Details - {{ item.country }}</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        header {
            background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        h1 {
            font-size: 1.8rem;
        }
        
        .back-btn {
            background-color: rgba(255, 255, 255, 0.2);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        
        .back-btn:hover {
            background-color: rgba(255, 255, 255, 0.3);
        }
        
        .content {
            padding: 30px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        .image-section {
            text-align: center;
        }
        
        .coin-image {
            max-width: 100%;
            max-height: 400px;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .no-image {
            padding: 60px 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
            color: #6c757d;
            font-style: italic;
        }
        
        .details-section h2 {
            color: #4a6ee0;
            margin-bottom: 20px;
            border-bottom: 2px solid #f0f4ff;
            padding-bottom: 10px;
        }
        
        .detail-grid {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .detail-label {
            font-weight: bold;
            color: #666;
        }
        
        .detail-value {
            color: #333;
        }
        
        .note-section {
            margin-top: 20px;
            padding: 15px;
            background-color: #f8f9ff;
            border-radius: 8px;
            border-left: 4px solid #4a6ee0;
        }
        
        .hidden-note {
            margin-top: 15px;
            padding: 10px;
            background-color: #fffbe6;
            border-radius: 5px;
            font-size: 0.9rem;
        }
        
        .navigation {
            display: flex;
            justify-content: space-between;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #f0f4ff;
        }
        
        .nav-btn {
            background-color: #4a6ee0;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
        }
        
        .nav-btn:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        
        @media (max-width: 768px) {
            .content {
                grid-template-columns: 1fr;
            }
            
            .navigation {
                flex-direction: column;
                gap: 10px;
            }
            
            .nav-btn {
                text-align: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{{ item.country }} - Coin Details</h1>
            <a href="javascript:history.back()" class="back-btn">← Back to List</a>
        </header>
        
        <div class="content">
            <div class="image-section">
                {% if image_path %}
                    <img src="/images/{{ item.country|urlencode }}/{{ item.image }}" 
                         alt="{{ item.country }} {{ item.year }} {{ item.currency_type }}" 
                         class="coin-image">
                {% else %}
                    <div class="no-image">
                        <h3>No Image Available</h3>
                        <p>Image path: images/{{ item.country }}/{{ item.image }}</p>
                    </div>
                {% endif %}
            </div>
            
            <div class="details-section">
                <h2>Item Information</h2>
                
                <div class="detail-grid">
                    <div class="detail-label">Country:</div>
                    <div class="detail-value">{{ item.country }}</div>
                    
                    <div class="detail-label">Box:</div>
                    <div class="detail-value">{{ item.box if item.box else 'Not assigned' }}</div>
                    
                    <div class="detail-label">Currency Type:</div>
                    <div class="detail-value">{{ item.currency_type if item.currency_type else 'Unknown' }}</div>
                    
                    <div class="detail-label">Year:</div>
                    <div class="detail-value">{{ item.year if item.year else 'Unknown' }}</div>
                    
                    <div class="detail-label">Size:</div>
                    <div class="detail-value">{{ item.size if item.size else 'Not specified' }}</div>
                    
                    <div class="detail-label">Donor:</div>
                    <div class="detail-value">{{ item.donor_name if item.donor_name else 'Unknown' }}</div>
                    
                    <div class="detail-label">Image File:</div>
                    <div class="detail-value">{{ item.image if item.image else 'No image' }}</div>
                </div>
                
                {% if item.note %}
                <div class="note-section">
                    <h3>Description</h3>
                    <p>{{ item.note }}</p>
                </div>
                {% endif %}
                
                {% if item.hidden_note %}
                <div class="hidden-note">
                    <strong>Additional Notes:</strong>
                    <p>{{ item.hidden_note }}</p>
                </div>
                {% endif %}
                
                {% if item.url and item.url != 'N/A' %}
                <div style="margin-top: 20px;">
                    <a href="{{ item.url }}" target="_blank" class="nav-btn">View Online</a>
                </div>
                {% endif %}
            </div>
        </div>
        
        <div class="navigation">
            <a href="/item/{{ item_id - 1 }}" class="nav-btn" {% if item_id <= 0 %}style="visibility: hidden;"{% endif %}>
                ← Previous Item
            </a>
            
            <span>Item {{ item_id + 1 }} of {{ total_items }}</span>
            
            <a href="/item/{{ item_id + 1 }}" class="nav-btn" {% if item_id >= total_items - 1 %}style="visibility: hidden;"{% endif %}>
                Next Item →
            </a>
        </div>
    </div>
</body>
</html>
'''

def render_template_string(template, **context):
    """Render template from string"""
    from flask import render_template_string as flask_render_template_string
    return flask_render_template_string(template, **context)

if __name__ == '__main__':
    # Create images directory if it doesn't exist
    os.makedirs('images', exist_ok=True)
    
    # Check if JSON file exists, if not create with empty array
    if not os.path.exists(JSON_FILE_PATH):
        save_data([])
        print(f"Created empty JSON file at {JSON_FILE_PATH}")
    
    app.run(debug=True, port=5000)