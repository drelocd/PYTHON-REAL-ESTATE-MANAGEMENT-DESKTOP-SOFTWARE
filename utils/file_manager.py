# real_estate_system/utils/file_manager.py
import os
import shutil
from datetime import datetime

# Centralized path definitions (could also be passed from main)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Go up two levels from utils
DATA_DIR = os.path.join(BASE_DIR, 'data')
PROPERTY_IMAGES_DIR = os.path.join(DATA_DIR, 'images')
TITLE_DEEDS_DIR = os.path.join(DATA_DIR, 'deeds')
RECEIPTS_DIR = os.path.join(DATA_DIR, 'receipts') # Add this if you generate receipts
SURVEY_ATTACHMENTS_DIR = os.path.join(DATA_DIR, 'survey_attachments') # Add this

def ensure_data_directories_exist():
    """Ensures all necessary data directories exist."""
    os.makedirs(PROPERTY_IMAGES_DIR, exist_ok=True)
    os.makedirs(TITLE_DEEDS_DIR, exist_ok=True)
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    os.makedirs(SURVEY_ATTACHMENTS_DIR, exist_ok=True)
    print(f"Ensured data directories exist under: {DATA_DIR}")

def save_files(source_paths, destination_dir):
    """
    Saves multiple files to the specified directory and returns a
    comma-separated string of their relative paths.
    """
    saved_paths = []
    if not source_paths:
        return None

    for source_path in source_paths:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        filename, file_extension = os.path.splitext(os.path.basename(source_path))
        new_filename = f"{filename}_{timestamp}{file_extension}"
        destination_path = os.path.join(destination_dir, new_filename)

        try:
            shutil.copy2(source_path, destination_path)
            # Store path relative to DATA_DIR (e.g., 'images/my_pic.jpg')
            relative_path = os.path.relpath(destination_path, DATA_DIR).replace("\\", "/")
            saved_paths.append(relative_path)
        except Exception as e:
            print(f"File Save Error: Failed to save file {source_path}: {e}")
            # You might want to re-raise or handle this error more robustly
            return None # Or return the paths that were successfully saved

    return ",".join(saved_paths)

def get_full_path(relative_path):
    """Converts a relative path stored in DB to a full absolute path."""
    if relative_path is None:
        return None
    return os.path.join(DATA_DIR, relative_path)

# You can initialize the directories when this module is imported or in main.py
ensure_data_directories_exist()