import json
import uuid

def modify_json_file(file_path, add_id_flag):
    """
    Modifies a JSON file by either adding or removing the 'id' field
    based on the value of a flag.

    Args:
        file_path (str): The path to the JSON file.
        add_id_flag (bool): If True, adds a 'uuid' id; if False, removes the 'id'.
    """
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: The file at {file_path} is not a valid JSON file.")
        return

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
            
    # Write the modified data back to the file with proper indentation
    with open(file_path, 'w') as file:
        json.dump(modified_data, file, indent=2)
    
    action = "added 'id' field with a UUID" if add_id_flag else "removed 'id' field"
    print(f"Successfully {action} to all items in {file_path}.")

# Example usage:
file_path = 'images/coins.json'

# To remove the 'id' field from the JSON file:
modify_json_file(file_path, False)

# To add the 'id' field with a UUID to the JSON file:
# modify_json_file(file_path, True)