import os
import csv

# Filepath of the CSV file
csv_file_path = "australian_postcodes.csv"

# Base directory for the output Markdown files
output_base_dir = "content/suburbs"

# Ensure the output directory exists
os.makedirs(output_base_dir, exist_ok=True)

def create_markdown_file(state, postcode, suburb_name, latitude, longitude):
    # Create the directory structure: /state/suburb-name
    suburb_dir = os.path.join(output_base_dir, state.lower())
    os.makedirs(suburb_dir, exist_ok=True)

    # Filepath for the Markdown file
    file_path = os.path.join(suburb_dir, f"{suburb_name.lower().replace(' ', '-')}.md")

    # Generate permalink in lowercase and without the postcode
    permalink = f"/{state.lower()}/{suburb_name.lower().replace(' ', '-')}/"
    
    # Markdown content with frontmatter
    content = f"""---
title: {suburb_name}
state: {state}
postcode: {postcode}
latitude: {latitude}
longitude: {longitude}
url: {permalink}
layout: suburb
---
"""

    # Write or overwrite the file
    with open(file_path, "w") as file:
        file.write(content)

def process_csv():
    with open(csv_file_path, "r") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            # Extract relevant fields
            state = row["state"]
            postcode = row["postcode"]
            suburb_name = row["locality"]
            latitude = row["lat"]
            longitude = row["long"]

            # Skip rows with missing data
            if not (state and postcode and suburb_name and latitude and longitude):
                continue

            # Create or update the Markdown file
            create_markdown_file(state, postcode, suburb_name, latitude, longitude)

if __name__ == "__main__":
    process_csv()