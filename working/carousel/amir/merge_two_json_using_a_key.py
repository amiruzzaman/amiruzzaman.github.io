import json

def merge_json_files(file1, file2, merge_key):
    """Merges two JSON files based on a specified key."""
    
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        data1 = json.load(f1)
        data2 = json.load(f2)

    merged_data = []

    # Create a dictionary to store merged items by the merge_key
    merged_dict = {item[merge_key]: item for item in data1}

    # Merge data from data2 into data1, based on the specified merge_key
    for item2 in data2:
        key_value = item2[merge_key]
        if key_value in merged_dict:
            merged_dict[key_value].update(item2)
        else:
            merged_dict[key_value] = item2

    # Convert merged_dict back to a list to match the original structure
    merged_data = list(merged_dict.values())

    return merged_data

# Example usage
file1 = 'images/coins.json'
file2 = 'images/coins2.json'
merge_key = 'image'

merged_data = merge_json_files(file1, file2, merge_key)

# Output the merged data to a file
with open('merged_coins.json', 'w') as outfile:
    json.dump(merged_data, outfile, indent=4)

# Also print it for verification
print(json.dumps(merged_data, indent=4))
