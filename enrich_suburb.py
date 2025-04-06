import os
import random
import sys
import json
from datetime import datetime, timezone
import requests

# Check for required libraries first
try:
    import google.generativeai as genai
    import frontmatter
    import yaml
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Missing required library: {e.name}")
    print("Please install required libraries using:")
    print("pip install google-generativeai python-frontmatter PyYAML python-dotenv")
    sys.exit(1)

# --- Configuration ---
CONTENT_DIR = "content/suburbs"
FACTS_KEY = "facts"  # Key for facts in front matter
LOCATIONS_KEY = "tourist_locations"  # Key for locations
NOTABLE_PEOPLE_KEY = "notable_people"  # Key for notable people
HISTORICAL_EVENTS_KEY = "historical_events"  # Key for historical events
MODEL_NAME = "gemini-1.5-pro-latest"  # Or other suitable Gemini model
# --- End Configuration ---

# --- Safety Settings for Gemini ---
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]
GENERATION_CONFIG = {
    "temperature": 0.7,
    "top_p": 1.0,
    "top_k": 32,
    "max_output_tokens": 1024,
    "response_mime_type": "application/json",
}
# --- End Safety Settings ---

def is_valid_url(url):
    """Check if a URL is valid and returns a success status (HTTP 200)."""
    try:
        response = requests.head(url, timeout=5)  # Use HEAD to minimize data transfer
        return response.status_code == 200
    except requests.RequestException:
        return False

def find_markdown_files(directory):
    """Recursively finds all .md files in a directory, excluding _index.md."""
    md_files = []
    abs_dir = os.path.abspath(directory)
    if not os.path.isdir(abs_dir):
        print(f"Error: Content directory not found: {abs_dir}")
        return None
    for subdir, _, files in os.walk(abs_dir):
        for filename in files:
            if filename.lower().endswith(".md") and filename != "_index.md":
                md_files.append(os.path.join(subdir, filename))
    return md_files

def get_gemini_data(suburb_name, state):
    """Queries Gemini API for facts, locations (with URLs), notable people, and historical events."""
    print(f"\nQuerying Gemini for {suburb_name}, {state}...")

    prompt = f"""
    Provide information about the suburb "{suburb_name}" in the state "{state}", Australia.
    Please return the response strictly as a JSON object with four keys:
    1.  "facts": A list containing exactly 10 interesting facts about this suburb.
    2.  "tourist_locations": A list of objects for tourist locations or points of interest in or very near this suburb. Each object **must** contain a "name" (string). **If** you can find a valid and relevant website link (specific official site, park page, museum page, or a suitable general tourism website URL for the area like the council or state tourism site), include it as a "url" (string) key in the object. **If no suitable URL is found, omit the "url" key entirely for that location object.** Aim for up to 10 locations.
    3.  "notable_people": A list containing up to 10 famous or notable people who live or have lived in this suburb.
    4.  "historical_events": A list containing up to 10 notable historical events that occurred in this suburb.

    Example JSON format (note "Location 2" has no "url"):
    {{
    "facts": ["Fact 1", "Fact 2", ..., "Fact 10"],
    "tourist_locations": [
        {{"name": "Specific Location 1", "url": "https://specific-site.example.com"}},
        {{"name": "Location 2 With No URL Found"}},
        {{"name": "Location 3 With General URL", "url": "https://general-regional-tourism.example.com"}}
    ],
    "notable_people": ["Person 1", "Person 2", ..., "Person 10"],
    "historical_events": ["Event 1", "Event 2", ..., "Event 10"]
    }}

    If the suburb is very small or obscure and you cannot find 10 distinct facts, locations, people, or events, provide as many as you can find that meet the criteria, up to the limit of 10 for each category, but still maintain the list format within the JSON structure. If you find absolutely nothing fitting the criteria for a category, return an empty list for that key (e.g., `"tourist_locations": []`).
    """

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            safety_settings=SAFETY_SETTINGS,
            generation_config=GENERATION_CONFIG
        )
        response = model.generate_content(prompt)

        # Attempt to parse the JSON response
        data = json.loads(response.text)

        # Validate structure and extract lists
        facts = data.get(FACTS_KEY, [])
        locations = data.get(LOCATIONS_KEY, [])
        notable_people = data.get(NOTABLE_PEOPLE_KEY, [])
        historical_events = data.get(HISTORICAL_EVENTS_KEY, [])

        if not all(isinstance(lst, list) for lst in [facts, notable_people, historical_events]) or not isinstance(locations, list):
            print("Error: Gemini response did not contain valid lists for all keys.")
            return None, None, None, None

        print(f"Successfully retrieved {len(facts)} facts, {len(locations)} locations, {len(notable_people)} notable people, and {len(historical_events)} historical events.")
        return facts, locations, notable_people, historical_events

    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON response from Gemini: {e}")
        return None, None, None, None
    except Exception as e:
        print(f"Error querying Gemini API: {e}")
        return None, None, None, None

def update_suburb_file(filepath, facts_list, locations_list, notable_people_list, historical_events_list):
    """Reads, updates front matter with facts/locations (with validated URLs)/notable_people/historical_events/lastmod, writes back."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        # Ensure tourist_locations is a list of dictionaries with "name" and optional "url"
        updated_locations = []
        for location in locations_list:
            if isinstance(location, str):  # BACKWARDS COMPATIBILITY: If it's a string, convert to a dict with just "name"
                updated_locations.append({"name": location})
            elif isinstance(location, dict):  # If it's already a dict (potentially with or without 'url'), keep it as is
                # Ensure name exists, even if URL is missing or blank
                if "name" in location:
                    if "url" in location and location["url"]:  # Validate the URL if it exists
                        if is_valid_url(location["url"]):
                            updated_locations.append(location)  # Add only if the URL is valid
                        else:
                            print(f"Invalid URL skipped: {location['url']}")
                    else:
                        updated_locations.append({"name": location["name"]})  # Add without URL
                # else: Optional: warn about malformed dict from Gemini if desired
            # else: Optional: handle unexpected types if necessary

        # Update metadata
        post.metadata[FACTS_KEY] = facts_list
        post.metadata[LOCATIONS_KEY] = updated_locations  # List of dicts with "name" and optional "url"
        post.metadata[NOTABLE_PEOPLE_KEY] = notable_people_list
        post.metadata[HISTORICAL_EVENTS_KEY] = historical_events_list
        post.metadata['lastmod'] = datetime.now(timezone.utc).isoformat(timespec='seconds')  # Update timestamp

        # Write back using binary mode for dump
        with open(filepath, 'wb') as f:
            frontmatter.dump(post, f, Dumper=yaml.SafeDumper)  # Use SafeDumper for broader compatibility
        return True
    except (yaml.YAMLError, FileNotFoundError, Exception) as e:
        print(f"Error updating file {filepath}: {e}")
        return False

def main():
    """Main script logic."""
    print("Starting suburb enrichment script...")

    # Load API Key from .env file
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in environment variables or .env file.")
        sys.exit(1)
    genai.configure(api_key=api_key)

    # Find all potential files
    all_files = find_markdown_files(CONTENT_DIR)
    if not all_files:
        print("No Markdown files found in the content directory.")
        sys.exit(1)

    print(f"Found {len(all_files)} potential suburb files.")

    # --- Select a random file ---
    selected_file = random.choice(all_files)
    print(f"\nSelected random file: {selected_file}")

    # --- Read the selected file and check if already processed ---
    try:
        with open(selected_file, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        if any(key in post.metadata for key in [FACTS_KEY, LOCATIONS_KEY, NOTABLE_PEOPLE_KEY, HISTORICAL_EVENTS_KEY]):
            print(f"Skipping: File already contains enrichment data.")
            sys.exit(0)  # Exit successfully, nothing to do

        # Extract needed info for prompt
        suburb_name = post.metadata.get('title')
        state = post.metadata.get('state')

        if not suburb_name or not state:
            print(f"Skipping: Missing 'title' or 'state' in front matter for {selected_file}.")
            sys.exit(1)  # Exit with error, file is malformed for our purpose

    except (yaml.YAMLError, FileNotFoundError, Exception) as e:
        print(f"Error reading or parsing {selected_file}: {e}")
        sys.exit(1)  # Exit with error

    # --- Query Gemini ---
    facts_list, locations_list, notable_people_list, historical_events_list = get_gemini_data(suburb_name, state)

    # --- Update file if data received ---
    if all(lst is not None for lst in [facts_list, locations_list, notable_people_list, historical_events_list]):
        if update_suburb_file(selected_file, facts_list, locations_list, notable_people_list, historical_events_list):
            print(f"\nSuccessfully updated {selected_file} with Gemini data.")
        else:
            print(f"\nFailed to update {selected_file} after retrieving data.")
    else:
        print("\nSkipping file update due to errors retrieving data from Gemini.")

    print("\nScript finished.")


if __name__ == "__main__":
    main()