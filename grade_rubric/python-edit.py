import json
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename

def load_json():
    # Prompt the user to select a JSON file to open
    Tk().withdraw()  # Hide the root window
    file_path = askopenfilename(filetypes=[("JSON files", "*.json")])
    if file_path:
        with open(file_path, 'r') as f:
            data = json.load(f)
        print("File loaded successfully.")
        return data
    else:
        print("No file selected.")
        return None

def save_json(data, filename="a2fall24.json"):
    # Prompt user for custom filename; default to "a2fall24.json" if none provided
    Tk().withdraw()  # Hide the root window
    save_path = asksaveasfilename(defaultextension=".json", initialfile=filename, filetypes=[("JSON files", "*.json")])
    if save_path:
        with open(save_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"File saved as {save_path}")
    else:
        print("File save canceled.")

# Example usage:
data = load_json()
if data is not None:
    # Here you can modify `data` as needed before saving
    data["new_key"] = "new_value"  # Example modification
    save_json(data)  # Prompt user to save file
