import os
import frontmatter
import yaml
import sys
from collections import Counter

# --- Configuration ---
# Adjust this path if your script is not in the hugo project root
CONTENT_DIR = "content/suburbs"
EXPECTED_KEY = "state"
# --- End Configuration ---

try:
    import frontmatter
    import yaml
except ImportError:
    print("Error: Required libraries 'python-frontmatter' or 'PyYAML' not found.")
    print("Please install them using: pip install python-frontmatter PyYAML")
    sys.exit(1)

parsing_errors = []
missing_key = []
empty_value = []
non_string_value = []
whitespace_value = []
incorrect_case_key = []
ok_files = 0
processed_files = 0

print(f"Scanning Markdown files in '{CONTENT_DIR}'...")
print(f"Expecting front matter key: '{EXPECTED_KEY}'")
print("-" * 30)

abs_content_dir = os.path.abspath(CONTENT_DIR)
if not os.path.isdir(abs_content_dir):
     print(f"Error: Directory not found: {abs_content_dir}")
     print("Please run this script from your Hugo project's root directory,")
     print(f"or adjust the CONTENT_DIR variable in the script.")
     sys.exit(1)


for subdir, dirs, files in os.walk(abs_content_dir):
    # Skip directories if needed (e.g., hidden ones) - usually not necessary here
    # dirs[:] = [d for d in dirs if not d.startswith('.')]

    for filename in files:
        # Process only Markdown files, exclude the section index file
        if filename.lower().endswith(".md") and filename != "_index.md":
            processed_files += 1
            filepath = os.path.join(subdir, filename)
            relative_path = os.path.relpath(filepath, abs_content_dir) # For cleaner reporting

            try:
                # Load the file, handling potential encoding issues
                with open(filepath, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)

                if not post.metadata:
                    parsing_errors.append((relative_path, "Empty front matter (metadata) section"))
                    continue # Skip further checks for this file

                metadata = post.metadata

                # 1. Check if the EXACT expected key exists
                if EXPECTED_KEY not in metadata:
                    missing_key.append(relative_path)
                    # Check for common case variations ONLY if exact key is missing
                    found_case = False
                    for key in metadata:
                        if key.lower() == EXPECTED_KEY.lower():
                            incorrect_case_key.append((relative_path, f"Found key '{key}'"))
                            found_case = True
                            break
                    if found_case:
                        # Don't count as missing if it's just a case issue
                         missing_key.pop() # Remove from missing list
                    continue # Go to next file after handling missing/case issue

                # 2. Key exists, check its value
                state_value = metadata[EXPECTED_KEY]

                if state_value is None:
                    empty_value.append((relative_path, "Value is None"))
                # Check if it's a string before stripping
                elif isinstance(state_value, str):
                    if state_value.strip() == "":
                         empty_value.append((relative_path, "Value is empty string or only whitespace"))
                    elif state_value != state_value.strip():
                         whitespace_value.append((relative_path, f"Value has leading/trailing whitespace: '{state_value}'"))
                    else:
                        # Passed string checks
                         ok_files += 1
                else: # Not None, not a string
                    non_string_value.append((relative_path, f"Type is {type(state_value).__name__}, not string. Value: {state_value!r}"))

            except (yaml.YAMLError, frontmatter.exceptions.FrontmatterError) as e:
                parsing_errors.append((relative_path, f"YAML/Frontmatter parsing error: {e}"))
            except UnicodeDecodeError as e:
                 parsing_errors.append((relative_path, f"File encoding error: {e}. Try saving as UTF-8."))
            except Exception as e: # Catch other potential file reading errors
                parsing_errors.append((relative_path, f"Unexpected error processing file: {e}"))


print("\n--- Validation Summary ---")
print(f"Processed {processed_files} '.md' files (excluding _index.md).")

error_found = False

if parsing_errors:
    error_found = True
    print(f"\n❌ Found {len(parsing_errors)} files with parsing/reading errors:")
    for file, err in parsing_errors[:20]: # Show first 20
        print(f"  - {file}: {err}")
    if len(parsing_errors) > 20: print("    (and more...)")

if missing_key:
    error_found = True
    print(f"\n❌ Found {len(missing_key)} files MISSING the '{EXPECTED_KEY}' key:")
    for file in missing_key[:20]: print(f"  - {file}")
    if len(missing_key) > 20: print("    (and more...)")

if incorrect_case_key:
    error_found = True
    print(f"\n⚠️ Found {len(incorrect_case_key)} files with INCORRECT CASE for the '{EXPECTED_KEY}' key (e.g., 'State'):")
    for file, detail in incorrect_case_key[:20]: print(f"  - {file} ({detail})")
    if len(incorrect_case_key) > 20: print("    (and more...)")

if empty_value:
    error_found = True
    print(f"\n❌ Found {len(empty_value)} files with EMPTY or None value for '{EXPECTED_KEY}':")
    for file, detail in empty_value[:20]: print(f"  - {file} ({detail})")
    if len(empty_value) > 20: print("    (and more...)")

if non_string_value:
    error_found = True
    print(f"\n❌ Found {len(non_string_value)} files where '{EXPECTED_KEY}' value is NOT A STRING:")
    for file, detail in non_string_value[:20]: print(f"  - {file} ({detail})")
    if len(non_string_value) > 20: print("    (and more...)")

if whitespace_value:
    error_found = True
    print(f"\n⚠️ Found {len(whitespace_value)} files where '{EXPECTED_KEY}' value has LEADING/TRAILING WHITESPACE:")
    for file, detail in whitespace_value[:20]: print(f"  - {file} ({detail})")
    if len(whitespace_value) > 20: print("    (and more...)")


print("-" * 30)
if not error_found:
    print(f"✅ All {processed_files} processed files seem OK regarding the '{EXPECTED_KEY}' key.")
else:
    print(f"⚠️ Found potential issues in front matter. Please review the files listed above.")
    print(f"   ({ok_files} files passed all checks for the '{EXPECTED_KEY}' key).")
print("-" * 30)