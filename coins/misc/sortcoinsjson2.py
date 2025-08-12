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
    """Loads coin data from a JSON file."""
    global coins_data, data_file_path
    data_file_path = os.path.abspath(file_path)
    print(f"Loading data from: {data_file_path}")
    with open(data_file_path, 'r', encoding='utf-8') as f:
        coins_data = json.load(f)
    return coins_data

def save_data():
    """Saves the current coin data to the JSON file."""
    global coins_data, data_file_path
    if not data_file_path:
        raise ValueError("No file path specified")
    print(f"Saving data to: {data_file_path}")
    with open(data_file_path, 'w', encoding='utf-8') as f:
        json.dump(coins_data, f, indent=2, ensure_ascii=False)

@app.route('/')
def index():
    """Renders the main application page."""
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Currency Collection Manager</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://code.jquery.com/ui/1.13.1/jquery-ui.min.js"></script>
    <style>
        body {
            font-family: 'Inter', sans-serif;
        }
        /* Custom scrollbar for better aesthetics */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #f1f5f9; /* slate-100 */
        }
        ::-webkit-scrollbar-thumb {
            background: #cbd5e1; /* slate-300 */
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8; /* slate-400 */
        }
        .ui-sortable-helper {
            display: table;
        }
    </style>
</head>
<body class="bg-slate-50 text-slate-800">
    <div class="container mx-auto p-4 md:p-8">
        <div class="bg-white p-6 md:p-8 rounded-xl shadow-lg border border-slate-200">
            <h1 class="text-3xl md:text-4xl font-bold mb-2 text-center text-slate-900">
                Currency Collection Manager
            </h1>
            <p class="text-center text-slate-500 mb-8">
                Manage your coin collection, re-order, and save changes.
            </p>
            
            <div class="file-input mb-6">
                <label for="json-file" class="block text-sm font-medium text-slate-700 mb-2">
                    Load JSON File:
                </label>
                <input type="file" id="json-file" accept=".json"
                    class="block w-full text-sm text-slate-500
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-full file:border-0
                    file:text-sm file:font-semibold
                    file:bg-indigo-50 file:text-indigo-700
                    hover:file:bg-indigo-100 cursor-pointer"
                >
                <div id="file-status" class="mt-2 text-sm text-slate-600"></div>
                <div id="file-path" class="text-xs text-slate-400 mt-1"></div>
            </div>
            
            <div class="flex flex-col md:flex-row gap-4 mb-6">
                <button id="sort-country-btn" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-lg transition duration-200 shadow-md">
                    Sort by Country
                </button>
                <button id="sort-currency-btn" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-lg transition duration-200 shadow-md">
                    Sort by Currency Type
                </button>
            </div>
            
            <div class="mb-6">
                <label for="search-input" class="block text-sm font-medium text-slate-700 mb-2">
                    Search by Country:
                </label>
                <input type="text" id="search-input" placeholder="e.g., United States"
                    class="block w-full px-4 py-2 border border-slate-300 rounded-lg shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                >
            </div>

            <div class="overflow-x-auto relative shadow-md sm:rounded-lg">
                <table id="coin-table" class="w-full text-sm text-left text-slate-500">
                    <thead class="text-xs text-slate-700 uppercase bg-slate-50">
                        <tr>
                            <th scope="col" class="px-6 py-3">Sort</th>
                            <th scope="col" class="px-6 py-3">Country</th>
                            <th scope="col" class="px-6 py-3">Currency Type</th>
                            <th scope="col" class="px-6 py-3">Donor Name</th>
                            <th scope="col" class="px-6 py-3">Note</th>
                            <th scope="col" class="px-6 py-3">Image</th>
                        </tr>
                    </thead>
                    <tbody id="coin-table-body" class="bg-white divide-y divide-slate-200">
                        </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <div id="image-modal" class="fixed inset-0 z-50 hidden bg-black bg-opacity-80 flex items-center justify-center p-4">
        <span id="modal-close" class="absolute top-4 right-4 text-white text-5xl font-thin cursor-pointer leading-none">&times;</span>
        <img id="modal-image" class="max-w-full max-h-[90vh] rounded-lg shadow-xl" src="">
    </div>
    
    <script>
        let fullData = []; // This holds the complete, original dataset.
        let currentData = []; // This holds the data currently displayed (can be filtered).
        let saveTimeout = null;

        $(document).ready(function() {
            // Make table rows sortable
            $('#coin-table-body').sortable({
                handle: ".sort-handle",
                axis: "y",
                update: function(event, ui) {
                    // Rebuild the fullData array based on the new visual order of the sorted elements.
                    const newOrder = [];
                    const sortedCountryItems = [];
                    const otherItems = [];

                    // Identify the items in the currentData (visible, filtered) and the items not visible.
                    const currentCountries = new Set(currentData.map(item => item.country));
                    fullData.forEach(item => {
                        if (currentCountries.has(item.country)) {
                            sortedCountryItems.push(item);
                        } else {
                            otherItems.push(item);
                        }
                    });

                    // Reorder the sortedCountryItems based on the new visual order.
                    const newSortedCountryItems = [];
                    $(this).find('tr').each(function() {
                        const originalIndex = $(this).data('original-index');
                        newSortedCountryItems.push(fullData[originalIndex]);
                    });

                    // Reconstruct the fullData array by combining the reordered items and the rest.
                    fullData = newSortedCountryItems.concat(otherItems);

                    // Update currentData to reflect the new order and re-render the table.
                    currentData = [...newSortedCountryItems];
                    updateTable(currentData);
                    autoSaveData();
                }
            }).disableSelection();

            // File input change handler (auto-load when file is selected)
            $('#json-file').change(function() {
                const file = this.files[0];
                if (!file) return;
                
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    try {
                        const data = JSON.parse(e.target.result);
                        fullData = data;
                        currentData = [...fullData];
                        updateTable(currentData);
                        
                        $('#file-status').html(`<span class="text-green-600 font-semibold">Loaded: <strong>${file.name}</strong></span>`);
                        $('#file-path').text(`Location: ${file.path || 'Browser security restricts full path access'}`);
                        
                        $.post('/set-file-path', { 
                            name: file.name,
                            path: file.path || 'images/' + file.name
                        }, function(response) {
                            if (response.success) {
                                console.log('File path set successfully');
                            }
                        });
                    } catch (error) {
                        alert('Error parsing JSON: ' + error.message);
                    }
                };
                
                reader.readAsText(file);
            });
            
            // Sort buttons
            $('#sort-country-btn').click(function() {
                fullData.sort((a, b) => a.country.localeCompare(b.country));
                currentData = [...fullData];
                updateTable(currentData);
                $('#file-status').html('<span class="text-indigo-600">Sorted by Country</span>');
                autoSaveData();
            });
            
            $('#sort-currency-btn').click(function() {
                fullData.sort((a, b) => a.currency_type.localeCompare(b.currency_type));
                currentData = [...fullData];
                updateTable(currentData);
                $('#file-status').html('<span class="text-indigo-600">Sorted by Currency Type</span>');
                autoSaveData();
            });
            
            // Search input handler
            $('#search-input').on('keyup', function() {
                const searchTerm = $(this).val().toLowerCase();
                if (searchTerm) {
                    currentData = fullData.filter(item => item.country.toLowerCase().includes(searchTerm));
                } else {
                    currentData = [...fullData];
                }
                updateTable(currentData);
            });
            
            // Image modal
            $(document).on('click', '.image-preview', function() {
                const src = $(this).attr('src');
                $('#modal-image').attr('src', src);
                $('#image-modal').removeClass('hidden');
            });
            
            $('#modal-close').click(function() {
                $('#image-modal').addClass('hidden');
            });

            // Handle the case where the Python backend auto-loads data on start
            fetchData();
        });
        
        function fetchData() {
            $.get('/get-initial-data', function(response) {
                if (response.success) {
                    fullData = response.data;
                    currentData = [...fullData];
                    updateTable(currentData);
                    $('#file-status').html(`<span class="text-green-600 font-semibold">Loaded: <strong>${response.path.split('/').pop()}</strong></span>`);
                    $('#file-path').text(`Location: ${response.path}`);
                } else {
                    $('#file-status').html(`<span class="text-red-600">No data loaded. Please select a JSON file.</span>`);
                }
            });
        }
        
        function updateTable(data) {
            const tableBody = $('#coin-table-body');
            tableBody.empty(); // Clear existing rows
            
            data.forEach((item, index) => {
                const countryFolder = item.country.replace(/ /g, '_');
                const imagePath = `/images/${countryFolder}/${item.image}`;
                
                // Find the original index from the fullData array
                const originalIndex = fullData.findIndex(d => d === item);

                const row = `
                    <tr data-index="${index}" data-original-index="${originalIndex}" class="bg-white border-b hover:bg-slate-50">
                        <td class="px-6 py-4 whitespace-nowrap w-12 cursor-grab text-xl text-slate-400">
                            <span class="sort-handle">☰</span>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap font-medium text-slate-900">${item.country}</td>
                        <td class="px-6 py-4 whitespace-nowrap">${item.currency_type}</td>
                        <td class="px-6 py-4 whitespace-nowrap">${item.donor_name}</td>
                        <td class="px-6 py-4">${item.note}</td>
                        <td class="px-6 py-4">
                            <img src="${imagePath}" onerror="this.onerror=null;this.src='https://placehold.co/100x100/e2e8f0/64748b?text=No+Image';" class="image-preview w-24 h-24 object-cover rounded-lg shadow-sm cursor-pointer" title="Click to enlarge">
                        </td>
                    </tr>
                `;
                tableBody.append(row);
            });
        }
        
        function autoSaveData() {
            // Clear any pending save
            if (saveTimeout) {
                clearTimeout(saveTimeout);
            }
            
            // Show saving status
            const status = $('#file-status');
            status.html('<span class="text-blue-600">Saving changes...</span>');
            
            // Save after a short delay (to prevent too many rapid saves)
            saveTimeout = setTimeout(() => {
                $.post('/save-data', { 
                    data: JSON.stringify(fullData)
                }, function(response) {
                    if (response.success) {
                        status.html(`<span class="text-green-600">Changes saved at ${new Date().toLocaleTimeString()}</span>`);
                        $('#file-path').text(response.path || '');
                    } else {
                        status.html(`<span class="text-red-600">Error: ${response.error}</span>`);
                    }
                }).fail(function() {
                    status.html('<span class="text-red-600">Failed to save data</span>');
                });
            }, 500);
        }
    </script>
</body>
</html>
    ''')

@app.route('/get-initial-data')
def get_initial_data():
    """Endpoint to get initial data for the front-end."""
    global coins_data, data_file_path
    if coins_data and data_file_path:
        return jsonify({
            'success': True,
            'data': coins_data,
            'path': data_file_path
        })
    return jsonify({
        'success': False,
        'message': 'No initial data available'
    })

@app.route('/set-file-path', methods=['POST'])
def set_file_path():
    """Sets the global data file path and loads the data."""
    global data_file_path, coins_data
    file_name = request.form['name']
    file_path = request.form.get('path', f'images/{file_name}')
    full_path = os.path.abspath(file_path)
    data_file_path = full_path
    
    # Check if the file exists and load it
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
    """Saves data received from the front-end."""
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
    """Serves images from the 'images' directory."""
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
    """Main function to set up and run the application."""
    Path(images_base_path).mkdir(exist_ok=True)
    
    # Try to load coins.json automatically
    default_path = os.path.join(images_base_path, 'coins.json')
    if os.path.exists(default_path):
        try:
            load_data(default_path)
            print(f"Auto-loaded data from: {default_path}")
        except Exception as e:
            print(f"Error auto-loading data: {str(e)}")
    
    webbrowser.open('http://127.0.0.1:5000')
    app.run(debug=True)

if __name__ == '__main__':
    run()