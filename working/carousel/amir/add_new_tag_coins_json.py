import json

# Load the JSON data
with open('./images/coins.json', 'r') as f:
    data = json.load(f)

# Add a new tag
# If 'data' is a list:
if isinstance(data, list):
    # You need to specify which element in the list to modify
    #data[0]['donar'] = 'new_value'
    for d in data:
        d['donar'] = 'new_value'
# If 'data' is a dictionary:
else:
    data['donar'] = 'new_value'

# Write the updated JSON data back to the file
with open('./images/coins.json', 'w') as f:
    json.dump(data, f, indent=4)  # indent for pretty formatting