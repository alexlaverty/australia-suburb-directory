import os
import csv
import frontmatter  # For reading/writing front matter
import yaml         # Required by frontmatter
from datetime import datetime, timezone # For timestamp
import sys

# --- Configuration ---
CSV_FILE_PATH = "australian_postcodes.csv"
OUTPUT_BASE_DIR = "content/suburbs"
# --- End Configuration ---

# Check for required libraries
try:
    import frontmatter
    import yaml
except ImportError:
    print("Error: Required libraries 'python-frontmatter' or 'PyYAML' not found.")
    print("Please install them using: pip install python-frontmatter PyYAML")
    sys.exit(1)


def create_or_update_markdown_file(state, postcode, suburb_name, latitude, longitude):
    """
    Creates a new Markdown file or updates an existing one.
    Updates 'lastmod' only if content fields change or file is new.
    """
    # Create the directory structure: /state/suburb-name
    # Use lower case for directory and file names for consistency
    state_dir_part = state.lower()
    suburb_file_part = suburb_name.lower().replace(' ', '-')
    suburb_dir = os.path.join(OUTPUT_BASE_DIR, state_dir_part)
    os.makedirs(suburb_dir, exist_ok=True)

    # Filepath for the Markdown file
    file_path = os.path.join(suburb_dir, f"{suburb_file_part}.md")

    # Generate permalink in lowercase
    permalink = f"/{state_dir_part}/{suburb_file_part}/"

    # Prepare the metadata dictionary from the CSV data
    new_metadata = {
        'title': suburb_name.upper(), # Keep title uppercase as before? Adjust if needed.
        'state': state,
        'postcode': postcode,
        'latitude': float(latitude), # Store as numbers if appropriate
        'longitude': float(longitude),
        'url': permalink,
        'layout': 'suburb'
        # 'lastmod' will be handled below
    }

    file_existed = os.path.exists(file_path)
    content_changed = False
    existing_post = None
    current_timestamp_iso = datetime.now(timezone.utc).isoformat(timespec='seconds')

    if file_existed:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_post = frontmatter.load(f)

            # Compare core data fields (ignore lastmod for comparison)
            fields_to_compare = ['title', 'state', 'postcode', 'latitude', 'longitude', 'url', 'layout']
            for key in fields_to_compare:
                # Handle potential type differences (e.g., float vs string)
                new_value = new_metadata.get(key)
                existing_value = existing_post.metadata.get(key)

                # Simple comparison, might need refinement for float precision if critical
                if str(new_value) != str(existing_value):
                    content_changed = True
                    print(f"   Change detected in '{key}': '{existing_value}' -> '{new_value}' for {file_path}")
                    break # No need to check further fields

        except yaml.YAMLError as e: # Catch specific YAML errors
            print(f"YAML parsing error reading existing file {file_path}: {e}. Overwriting.")
            content_changed = True
            file_existed = False
            existing_post = None
        except Exception as e: # Catch other general errors during read/load
            print(f"Error reading/loading existing file {file_path}: {e}. Overwriting.")
            content_changed = True
            file_existed = False
            existing_post = None

    # --- Determine final metadata and if writing is needed ---
    final_metadata = {}
    needs_writing = False

    if not file_existed:
        # New file: use new data and add current lastmod
        final_metadata = new_metadata
        final_metadata['lastmod'] = current_timestamp_iso
        needs_writing = True
        action = "Created"
    elif content_changed:
        # Existing file, content changed: merge, update lastmod
        final_metadata = existing_post.metadata.copy() # Start with existing
        final_metadata.update(new_metadata) # Overwrite with new values
        final_metadata['lastmod'] = current_timestamp_iso # Update timestamp
        needs_writing = True
        action = "Updated"
    else:
        # Existing file, content unchanged: do nothing
        needs_writing = False
        action = "Skipped (no changes)"

    # --- Write the file only if needed ---
    if needs_writing:
        # Reconstruct the post object to write
        # Use existing content body if available, otherwise empty
        content_body = existing_post.content if existing_post else ""
        post_to_write = frontmatter.Post(content=content_body, **final_metadata)

        try:
            with open(file_path, 'wb') as f: # Use 'wb' for binary write with frontmatter.dump
                frontmatter.dump(post_to_write, f)
            # print(f"{action}: {file_path}") # Uncomment for verbose output
        except Exception as e:
             print(f"Error writing file {file_path}: {e}")

    # Return the action taken for summary purposes
    return action


def process_csv():
    print(f"Processing CSV file: {CSV_FILE_PATH}")
    print(f"Output directory: {OUTPUT_BASE_DIR}")
    file_actions = {"Created": 0, "Updated": 0, "Skipped (no changes)": 0, "Errors": 0}
    row_count = 0

    try:
        with open(CSV_FILE_PATH, "r", encoding='utf-8') as csv_file: # Specify encoding
            reader = csv.DictReader(csv_file)
            for i, row in enumerate(reader):
                row_count = i + 1
                # Extract relevant fields
                try:
                    # Use .get() with default to handle potentially missing columns gracefully
                    state = row.get("state", "").strip()
                    postcode = row.get("postcode", "").strip()
                    suburb_name = row.get("locality", "").strip()
                    latitude = row.get("lat", "").strip()
                    longitude = row.get("long", "").strip()

                    # Skip rows with missing essential data
                    if not (state and postcode and suburb_name and latitude and longitude):
                        # print(f"Skipping row {row_count}: Missing essential data.")
                        continue

                    # Sanitize suburb name for filename (basic example)
                    if not suburb_name: continue # Cannot create file without name
                    # Additional sanitization might be needed for edge cases

                    # Create or update the Markdown file
                    action = create_or_update_markdown_file(state, postcode, suburb_name, latitude, longitude)
                    file_actions[action] += 1

                except KeyError as e:
                    print(f"Skipping row {row_count}: Missing expected column header '{e}'")
                    file_actions["Errors"] += 1
                except Exception as e:
                    print(f"Error processing row {row_count}: {e}")
                    file_actions["Errors"] += 1

                # Optional: Progress indicator
                if row_count % 1000 == 0:
                    print(f"Processed {row_count} rows...")

    except FileNotFoundError:
        print(f"Error: CSV file not found at '{CSV_FILE_PATH}'")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during CSV processing: {e}")
        sys.exit(1)

    print("\n--- Processing Summary ---")
    print(f"Total rows processed: {row_count}")
    print(f"Files Created: {file_actions['Created']}")
    print(f"Files Updated (content changed): {file_actions['Updated']}")
    print(f"Files Skipped (no changes): {file_actions['Skipped (no changes)']}")
    print(f"Rows with Errors/Skipped: {file_actions['Errors']}")
    print("--------------------------")


if __name__ == "__main__":
    # Ensure the output base directory exists
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
    process_csv()
    print("Script finished.")