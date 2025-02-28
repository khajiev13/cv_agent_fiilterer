import os
import logging
import uuid
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Define the base directory for storing CV files
CV_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cvs")

# Create the directory if it doesn't exist
os.makedirs(CV_DATA_DIR, exist_ok=True)

def save_uploaded_file(uploaded_file, unique_filename=None):
    """
    Save an uploaded file to the data/cvs directory
    
    Args:
        uploaded_file: The uploaded file object
        unique_filename: Optional unique filename to use
        
    Returns:
        tuple: (file_name, file_path)
    """
    # Create directory if it doesn't exist
    save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cvs")
    os.makedirs(save_dir, exist_ok=True)
    
    # Use provided unique filename or original filename
    file_name = unique_filename if unique_filename else uploaded_file.name
    file_path = os.path.join(save_dir, file_name)
    
    # Save the file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_name, file_path

def delete_cv_file(file_path):
    """
    Delete a CV file from the data directory
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        bool: True if deleted successfully, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted file {file_path}")
            return True
        else:
            logger.warning(f"File not found: {file_path}")
            return False
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        return False
