import json

# Function to parse the file content and create a JSON mapping
def create_country_geojson_mapping(input_file, output_file):
    mapping = []

    with open(input_file, "r") as file:
        for line in file:
            # Extract country name and file path using delimiters
            if line.startswith("-") and "[" in line and "]" in line and "(" in line and ")" in line:
                country_name = line[line.index("[") + 1:line.index("]")]
                file_path = line[line.index("(") + 1:line.index(")")]

                # Create a dictionary for each entry
                mapping.append({
                    "country_name": country_name,
                    "file_name": file_path.replace("../../../blob/master/", "")
                })

    # Write the mapping to a JSON file
    with open(output_file, "w") as json_file:
        json.dump(mapping, json_file, indent=4)

# Input and output file paths
input_file = "input.txt"  # Replace with the actual input file name
output_file = "country_geojson_mapping.json"

# Create the mapping
create_country_geojson_mapping(input_file, output_file)

print(f"Mapping saved to '{output_file}'")
