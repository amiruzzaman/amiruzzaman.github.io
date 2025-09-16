import json
from collections import defaultdict

def update_coins_json(file_path):
    # Read the JSON file
    with open(file_path, 'r', encoding='utf-8') as file:
        coins_data = json.load(file)
    
    # Create a dictionary to store box and hidden_note values by country
    country_info = defaultdict(dict)
    
    # First pass: collect box and hidden_note values for each country
    for coin in coins_data:
        country = coin.get('country')
        if country:
            if 'box' in coin:
                country_info[country]['box'] = coin['box']
            if 'hidden_note' in coin:
                country_info[country]['hidden_note'] = "" #coin['hidden_note'] updating using empty string instead of copying from other object
    
    # Second pass: update coins that are missing box or hidden_note
    for coin in coins_data:
        country = coin.get('country')
        if country and country in country_info:
            # Add box if missing
            if 'box' not in coin and 'box' in country_info[country]:
                coin['box'] = country_info[country]['box']
            
            # Add hidden_note if missing
            if 'hidden_note' not in coin and 'hidden_note' in country_info[country]:
                coin['hidden_note'] = country_info[country]['hidden_note']
    
    # Write the updated data back to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(coins_data, file, indent=2, ensure_ascii=False)
    
    print(f"Successfully updated {file_path}")

# Run the function
update_coins_json('images/coins.json')