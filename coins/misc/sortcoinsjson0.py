import json
import os
from pathlib import Path
import webbrowser
from flask import Flask, render_template_string, request, jsonify, send_from_directory

app = Flask(__name__)

# Global variables
coins_data = []
data_file_path = ""
images_base_path = "images"

def load_data(file_path):
    global coins_data, data_file_path
    data_file_path = os.path.abspath(file_path)
    print(f"Loading data from: {data_file_path}")
    with open(data_file_path, 'r', encoding='utf-8') as f:
        coins_data = json.load(f)
    return coins_data

def save_data():
    global coins_data, data_file_path
    if not data_file_path:
        raise ValueError("No file path specified")
    print(f"Saving data to: {data_file_path}")
    with open(data_file_path, 'w', encoding='utf-8') as f:
        json.dump(coins_data, f, indent=2, ensure_ascii=False)

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Currency Collection Manager</title>
    <meta charset="UTF-8">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://code.jquery.com/ui/1.13.1/jquery-ui.min.js"></script>
    <link rel="stylesheet" href="https://code.jquery.com/ui/1.13.1/themes/base/jquery-ui.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.min.css">
    <script src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .file-input {
            margin-bottom: 20px;
        }
        #coin-table {
            width: 100%;
            margin-top: 20px;
        }
        .image-preview {
            max-width: 100px;
            max-height: 100px;
        }
        .sort-handle {
            cursor: move;
            color: #ccc;
        }
        #image-modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.9);
        }
        #modal-image {
            display: block;
            max-width: 80%;
            max-height: 80%;
            margin: 60px auto;
        }
        #modal-close {
            position: absolute;
            top: 15px;
            right: 35px;
            color: #f1f1f1;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
        }
        .controls {
            margin: 10px 0;
        }
        button {
            padding: 5px 10px;
            margin-right: 5px;
        }
        .file-path {
            margin-top: 10px;
            font-family: monospace;
            font-size: 0.9em;
            color: #666;
        }
        #file-status {
            margin-top: 5px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Currency Collection Manager</h1>
        
        <div class="file-input">
            <input type="file" id="json-file" accept=".json">
            <button id="load-btn">Load JSON</button>
            <button id="save-btn">Save Changes</button>
            <div id="file-status"></div>
            <div id="file-path" class="file-path"></div>
        </div>
        
        <div class="controls">
            <button id="sort-country-btn">Sort by Country</button>
            <button id="sort-currency-btn">Sort by Currency Type</button>
        </div>
        
        <table id="coin-table" class="display">
            <thead>
                <tr>
                    <th>Sort</th>
                    <th>Country</th>
                    <th>Currency Type</th>
                    <th>Donor Name</th>
                    <th>Note</th>
                    <th>Image</th>
                </tr>
            </thead>
            <tbody id="coin-table-body">
                <!-- Data will be inserted here -->
            </tbody>
        </table>
    </div>
    
    <div id="image-modal">
        <span id="modal-close">&times;</span>
        <img id="modal-image">
    </div>
    
    <script>
        let table;
        let currentData = [];
        let originalData = [];
        
        $(document).ready(function() {
            // Initialize DataTable
            table = $('#coin-table').DataTable({
                paging: true,
                pageLength: 20,
                columns: [
                    { data: 'sort', orderable: false },
                    { data: 'country' },
                    { data: 'currency_type' },
                    { data: 'donor_name' },
                    { data: 'note' },
                    { data: 'image', orderable: false }
                ],
                columnDefs: [
                    { width: "50px", targets: 0 },
                    { width: "150px", targets: 1 },
                    { width: "120px", targets: 2 },
                    { width: "150px", targets: 3 },
                    { width: "250px", targets: 4 },
                    { width: "120px", targets: 5 }
                ]
            });
            
            // Make table rows sortable
            $('#coin-table tbody').sortable({
                handle: ".sort-handle",
                update: function(event, ui) {
                    updateCurrentDataOrder();
                }
            }).disableSelection();
            
            // File load handler
            $('#load-btn').click(function() {
                const fileInput = document.getElementById('json-file');
                if (fileInput.files.length === 0) {
                    alert('Please select a JSON file first');
                    return;
                }
                
                const file = fileInput.files[0];
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    try {
                        const data = JSON.parse(e.target.result);
                        originalData = data;
                        currentData = [...data];
                        updateTable(currentData);
                        
                        $('#file-status').html(`Loaded: <strong>${file.name}</strong>`).css('color', 'green');
                        $('#file-path').text(`Location: ${file.path || 'Browser security restricts full path access'}`);
                        
                        $.post('/set-file-path', { 
                            name: file.name,
                            path: file.path || 'images/' + file.name
                        });
                    } catch (error) {
                        alert('Error parsing JSON: ' + error.message);
                    }
                };
                
                reader.readAsText(file);
            });
            
            // Save button handler
            $('#save-btn').click(function() {
                if (currentData.length === 0) {
                    alert('No data loaded to save');
                    return;
                }
                
                // Get the current order of items
                updateCurrentDataOrder();
                
                $.post('/save-data', { 
                    data: JSON.stringify(currentData)
                }, function(response) {
                    if (response.success) {
                        $('#file-status').html(`<span style="color:green">${response.message}</span>`);
                        // Update original data after successful save
                        originalData = [...currentData];
                    } else {
                        $('#file-status').html(`<span style="color:red">Error: ${response.error}</span>`);
                    }
                    $('#file-path').text(response.path || '');
                }).fail(function() {
                    $('#file-status').html('<span style="color:red">Failed to save data</span>');
                });
            });
            
            // Sort buttons
            $('#sort-country-btn').click(function() {
                currentData.sort((a, b) => a.country.localeCompare(b.country));
                updateTable(currentData);
                $('#file-status').html('<span style="color:blue">Sorted by Country</span>');
            });
            
            $('#sort-currency-btn').click(function() {
                currentData.sort((a, b) => a.currency_type.localeCompare(b.currency_type));
                updateTable(currentData);
                $('#file-status').html('<span style="color:blue">Sorted by Currency Type</span>');
            });
            
            // Image modal
            $(document).on('click', '.image-preview', function() {
                const src = $(this).attr('src');
                $('#modal-image').attr('src', src);
                $('#image-modal').show();
            });
            
            $('#modal-close').click(function() {
                $('#image-modal').hide();
            });
        });
        
        function updateTable(data) {
            const rows = data.map((item, index) => {
                const countryFolder = item.country.replace(/ /g, '_');
                const imagePath = `/images/${countryFolder}/${item.image}`;
                
                return {
                    sort: `<span class="sort-handle">↕</span>`,
                    country: item.country,
                    currency_type: item.currency_type,
                    donor_name: item.donor_name,
                    note: item.note,
                    image: `<img src="${imagePath}" class="image-preview" title="Click to enlarge">`,
                    originalIndex: index
                };
            });
            
            table.clear().rows.add(rows).draw();
        }
        
        function updateCurrentDataOrder() {
            const newOrder = [];
            $('#coin-table tbody tr').each(function() {
                const rowData = table.row(this).data();
                if (rowData && rowData.originalIndex !== undefined) {
                    newOrder.push(originalData[rowData.originalIndex]);
                }
            });
            
            if (newOrder.length === originalData.length) {
                currentData = newOrder;
            }
        }
    </script>
</body>
</html>
    ''')

@app.route('/set-file-path', methods=['POST'])
def set_file_path():
    global data_file_path
    file_name = request.form['name']
    file_path = request.form.get('path', f'images/{file_name}')
    full_path = os.path.abspath(file_path)
    data_file_path = full_path
    print(f"Set file path to: {data_file_path}")
    
    # Try to load the data if the file exists
    if os.path.exists(data_file_path):
        try:
            load_data(data_file_path)
            return jsonify({
                'success': True,
                'message': f'Loaded {file_name}',
                'path': data_file_path,
                'data': coins_data
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error loading file: {str(e)}',
                'path': data_file_path
            })
    return jsonify({'success': True, 'path': data_file_path})

@app.route('/save-data', methods=['POST'])
def save_data_endpoint():
    try:
        data = json.loads(request.form['data'])
        if not isinstance(data, list):
            raise ValueError("Data must be an array")
        
        global coins_data
        coins_data = data
        save_data()
        
        return jsonify({
            'success': True,
            'message': f'Successfully saved {len(data)} items',
            'path': data_file_path,
            'data': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'path': data_file_path
        })

@app.route('/images/<country>/<filename>')
def serve_image(country, filename):
    country_folder = country.replace('_', ' ')
    directory = os.path.join(images_base_path, country_folder)
    
    # Case-insensitive file search
    if os.path.exists(directory):
        for f in os.listdir(directory):
            if f.lower() == filename.lower():
                filename = f
                break
    
    return send_from_directory(directory, filename)

def run():
    # Create images directory if it doesn't exist
    Path(images_base_path).mkdir(exist_ok=True)
    
    # Try to load coins.json automatically
    default_path = os.path.join(images_base_path, 'coins.json')
    if os.path.exists(default_path):
        try:
            load_data(default_path)
            print(f"Auto-loaded data from: {default_path}")
        except Exception as e:
            print(f"Error auto-loading data: {str(e)}")
    
    # Open browser automatically
    webbrowser.open('http://127.0.0.1:5000')
    
    # Run the Flask app
    app.run(debug=True)

if __name__ == '__main__':
    run()