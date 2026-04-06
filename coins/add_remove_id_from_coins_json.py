#!/usr/bin/env python3
"""
Complete Web Application: JSON ID Manager
Run this file with: python app.py
Browser will open automatically!
"""

from flask import Flask, render_template_string, request, jsonify
import json
import uuid
import webbrowser
import threading
import time
import sys

app = Flask(__name__)

# ============ YOUR ORIGINAL PYTHON LOGIC ============
def modify_json_data(data, add_id_flag):
    """
    Modifies JSON data by either adding or removing the 'id' field
    based on the value of a flag.
    
    Args:
        data (list): The JSON array data
        add_id_flag (bool): If True, adds a 'uuid' id; if False, removes the 'id'
    
    Returns:
        list: Modified data
    """
    modified_data = []
    for item in data:
        if add_id_flag:
            # Add 'id' field with a new UUID if it doesn't exist
            if 'id' not in item:
                item['id'] = str(uuid.uuid4())
            modified_data.append(item)
        else:
            # Remove 'id' field if it exists
            if 'id' in item:
                del item['id']
            modified_data.append(item)
    
    return modified_data
# ====================================================

# HTML/CSS/JavaScript Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JSON ID Manager | Python Backend</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        /* Header */
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }

        .header p {
            font-size: 1rem;
            opacity: 0.95;
        }

        .python-badge {
            background: #306998;
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            margin-top: 10px;
            font-family: monospace;
        }

        /* Toolbar */
        .toolbar {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            justify-content: space-between;
            align-items: center;
        }

        .mode-switch {
            display: flex;
            gap: 10px;
            background: #f0f0f0;
            padding: 5px;
            border-radius: 50px;
        }

        .mode-btn {
            padding: 10px 25px;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.3s;
            background: transparent;
            color: #666;
        }

        .mode-btn.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 2px 10px rgba(102,126,234,0.3);
        }

        .action-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 30px;
            border-radius: 50px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: transform 0.2s;
        }

        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102,126,234,0.4);
        }

        .file-label {
            background: #f0f0f0;
            padding: 10px 20px;
            border-radius: 50px;
            cursor: pointer;
            transition: background 0.2s;
        }

        .file-label:hover {
            background: #e0e0e0;
        }

        .status {
            background: #e8f5e9;
            padding: 10px 20px;
            border-radius: 50px;
            font-size: 0.9rem;
            color: #2e7d32;
        }

        /* Editor Panels */
        .panels {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }

        .panel {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }

        .panel-header {
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 2px solid #e9ecef;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .panel-header h3 {
            color: #333;
        }

        .badge {
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
        }

        .json-editor {
            width: 100%;
            height: 500px;
            padding: 20px;
            font-family: 'Courier New', 'Fira Code', monospace;
            font-size: 13px;
            border: none;
            resize: none;
            outline: none;
            background: #fafafa;
            line-height: 1.5;
        }

        .json-preview {
            background: #fafafa;
            padding: 20px;
            height: 500px;
            overflow: auto;
            font-family: 'Courier New', 'Fira Code', monospace;
            font-size: 13px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        /* Footer */
        .footer {
            background: white;
            border-radius: 15px;
            padding: 15px 20px;
            display: flex;
            gap: 15px;
            justify-content: flex-end;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }

        .secondary-btn {
            background: #6c757d;
            color: white;
            border: none;
            padding: 8px 20px;
            border-radius: 50px;
            cursor: pointer;
            transition: background 0.2s;
        }

        .secondary-btn:hover {
            background: #5a6268;
        }

        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        @media (max-width: 768px) {
            .panels {
                grid-template-columns: 1fr;
            }
            .toolbar {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔧 JSON ID Manager</h1>
            <p>Powered by Python + Flask • Same logic as your original script</p>
            <div class="python-badge">🐍 Python Backend • UUID v4</div>
        </div>

        <div class="toolbar">
            <div class="mode-switch">
                <button class="mode-btn active" data-mode="remove">🗑️ Remove 'id' Fields</button>
                <button class="mode-btn" data-mode="add">✨ Add UUID 'id' Fields</button>
            </div>
            <div>
                <label class="file-label">
                    📁 Load JSON File
                    <input type="file" id="fileInput" accept=".json" style="display: none;">
                </label>
            </div>
            <div class="status" id="status">✅ Ready • Remove mode active</div>
            <button class="action-btn" id="applyBtn">🔄 Apply Transformation</button>
        </div>

        <div class="panels">
            <div class="panel">
                <div class="panel-header">
                    <h3>📝 Input JSON (Array of Objects)</h3>
                    <span class="badge" id="inputCount">0 items</span>
                </div>
                <textarea class="json-editor" id="inputEditor" placeholder='[
  {
    "name": "Bitcoin",
    "symbol": "BTC",
    "price": 45000
  },
  {
    "name": "Ethereum", 
    "symbol": "ETH",
    "id": "existing-id-123"
  }
]'></textarea>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <h3>✨ Transformed Output (Python Processed)</h3>
                    <span class="badge" id="outputCount">0 items</span>
                </div>
                <div class="json-preview" id="outputPreview">Click "Apply Transformation" to see results...</div>
            </div>
        </div>

        <div class="footer">
            <button class="secondary-btn" id="resetBtn">↺ Reset Sample Data</button>
            <button class="secondary-btn" id="copyBtn">📋 Copy Output</button>
            <button class="secondary-btn" id="downloadBtn">💾 Download JSON</button>
        </div>
    </div>

    <script>
        let currentMode = 'remove';
        
        // Sample data matching your original example
        const sampleData = [
            {
                "name": "Bitcoin",
                "symbol": "BTC",
                "market_cap": "$1.2T"
            },
            {
                "name": "Ethereum",
                "symbol": "ETH",
                "id": "legacy-id-123e4567-e89b-12d3-a456-426614174000",
                "market_cap": "$500B"
            },
            {
                "name": "Cardano",
                "symbol": "ADA",
                "consensus": "PoS"
            },
            {
                "name": "Dogecoin",
                "symbol": "DOGE",
                "meme": true
            }
        ];

        // Initialize editor with sample data
        const editor = document.getElementById('inputEditor');
        const outputPreview = document.getElementById('outputPreview');
        const statusDiv = document.getElementById('status');
        const inputCountSpan = document.getElementById('inputCount');
        const outputCountSpan = document.getElementById('outputCount');

        editor.value = JSON.stringify(sampleData, null, 2);
        updateInputCount();

        // Mode switching
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentMode = btn.dataset.mode;
                const modeText = currentMode === 'remove' ? 'Remove' : 'Add UUID';
                statusDiv.innerHTML = `✅ ${modeText} mode active • Ready to transform`;
                statusDiv.style.background = currentMode === 'remove' ? '#e8f5e9' : '#fff3e0';
            });
        });

        // Apply transformation using Python backend
        async function applyTransformation() {
            try {
                // Parse input JSON
                const inputData = JSON.parse(editor.value);
                
                if (!Array.isArray(inputData)) {
                    throw new Error('Input must be a JSON array');
                }

                // Show loading state
                const applyBtn = document.getElementById('applyBtn');
                const originalText = applyBtn.innerHTML;
                applyBtn.innerHTML = '<span class="loading"></span> Processing...';
                applyBtn.disabled = true;

                // Send to Python backend
                const response = await fetch('/transform', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        data: inputData,
                        mode: currentMode
                    })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || 'Transformation failed');
                }

                const result = await response.json();
                
                // Display transformed data
                outputPreview.innerHTML = syntaxHighlight(JSON.stringify(result.data, null, 2));
                outputCountSpan.innerText = result.data.length;
                
                statusDiv.innerHTML = `✅ Transformation complete! ${currentMode === 'remove' ? 'Removed all id fields' : 'Added UUIDs where missing'}`;
                
                // Reset button
                applyBtn.innerHTML = originalText;
                applyBtn.disabled = false;
                
            } catch (error) {
                statusDiv.innerHTML = `❌ Error: ${error.message}`;
                statusDiv.style.background = '#ffebee';
                outputPreview.innerHTML = `<span style="color: #d32f2f;">Error: ${error.message}</span>`;
                
                const applyBtn = document.getElementById('applyBtn');
                applyBtn.innerHTML = '🔄 Apply Transformation';
                applyBtn.disabled = false;
            }
        }

        // Syntax highlighting for JSON
        function syntaxHighlight(json) {
            json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
                let cls = 'number';
                if (/^"/.test(match)) {
                    if (/:$/.test(match)) {
                        cls = 'key';
                    } else {
                        cls = 'string';
                    }
                } else if (/true|false/.test(match)) {
                    cls = 'boolean';
                } else if (/null/.test(match)) {
                    cls = 'null';
                }
                return '<span style="color: ' + getColor(cls) + ';">' + match + '</span>';
            });
        }

        function getColor(type) {
            switch(type) {
                case 'key': return '#881391';
                case 'string': return '#1a8813';
                case 'number': return '#1642b5';
                case 'boolean': return '#0e6b8c';
                default: return '#333';
            }
        }

        function updateInputCount() {
            try {
                const data = JSON.parse(editor.value);
                if (Array.isArray(data)) {
                    inputCountSpan.innerText = data.length + ' items';
                } else {
                    inputCountSpan.innerText = 'invalid';
                }
            } catch(e) {
                inputCountSpan.innerText = 'invalid JSON';
            }
        }

        // Load file
        document.getElementById('fileInput').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    editor.value = e.target.result;
                    updateInputCount();
                    statusDiv.innerHTML = `📁 Loaded: ${file.name}`;
                };
                reader.readAsText(file);
            }
        });

        // Reset to sample
        document.getElementById('resetBtn').addEventListener('click', () => {
            editor.value = JSON.stringify(sampleData, null, 2);
            updateInputCount();
            outputPreview.innerHTML = 'Click "Apply Transformation" to see results...';
            outputCountSpan.innerText = '0';
            statusDiv.innerHTML = '🔄 Reset to sample data';
        });

        // Copy output
        document.getElementById('copyBtn').addEventListener('click', async () => {
            const outputText = outputPreview.innerText;
            if (outputText && !outputText.includes('Click "Apply Transformation"')) {
                await navigator.clipboard.writeText(outputText);
                statusDiv.innerHTML = '📋 Output copied to clipboard!';
                setTimeout(() => {
                    statusDiv.innerHTML = '✅ Ready';
                }, 2000);
            } else {
                statusDiv.innerHTML = '⚠️ No output to copy. Apply transformation first.';
            }
        });

        // Download output
        document.getElementById('downloadBtn').addEventListener('click', () => {
            const outputText = outputPreview.innerText;
            if (outputText && !outputText.includes('Click "Apply Transformation"')) {
                const blob = new Blob([outputText], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = currentMode === 'remove' ? 'coins_without_ids.json' : 'coins_with_uuids.json';
                a.click();
                URL.revokeObjectURL(url);
                statusDiv.innerHTML = '💾 File downloaded!';
            } else {
                statusDiv.innerHTML = '⚠️ No output to download. Apply transformation first.';
            }
        });

        editor.addEventListener('input', updateInputCount);
        document.getElementById('applyBtn').addEventListener('click', applyTransformation);
        
        // Initial highlight
        updateInputCount();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/transform', methods=['POST'])
def transform():
    """
    API endpoint that uses your original Python logic
    """
    try:
        data = request.get_json()
        
        if not data or 'data' not in data or 'mode' not in data:
            return jsonify({'error': 'Missing required fields: data and mode'}), 400
        
        input_data = data['data']
        mode = data['mode']
        
        if not isinstance(input_data, list):
            return jsonify({'error': 'Data must be an array'}), 400
        
        if mode not in ['add', 'remove']:
            return jsonify({'error': 'Mode must be "add" or "remove"'}), 400
        
        # Call your original Python function!
        add_id_flag = (mode == 'add')
        modified_data = modify_json_data(input_data, add_id_flag)
        
        return jsonify({
            'success': True,
            'data': modified_data,
            'mode': mode,
            'count': len(modified_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def open_browser():
    """Open browser after server starts"""
    time.sleep(2)  # Wait 2 seconds for server to start
    url = 'http://localhost:5000'
    print(f"\n🌐 Opening browser at {url}...")
    webbrowser.open(url)

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 JSON ID Manager - Python Backend Server")
    print("=" * 60)
    print(f"📋 Using your original Python logic from remove_id_from_coins_json.py")
    print(f"🌐 Server will start at: http://localhost:5000")
    print(f"📁 Browser will open automatically in 2 seconds...")
    print(f"💡 If browser doesn't open, manually go to: http://localhost:5000")
    print("=" * 60)
    print()
    
    # Start browser in a separate thread
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Run the Flask app
    try:
        app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
        sys.exit(0)