import os
import logging
import uuid
from pathlib import Path
from datetime import datetime
import asyncio
import subprocess
from typing import Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import UnstructuredFileLoader
import io

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


async def read_cv_text(file_path: str) -> Optional[str]:
    """
    Read text from a CV file using LangChain document loaders
    
    Args:
        file_path: Path to the CV file
        
    Returns:
        str: Extracted text content, or None if extraction failed
    """
    try:
        file_name = os.path.basename(file_path)
        file_extension = Path(file_path).suffix.lower()
        
        # Load document based on file type
        if file_extension == '.txt':

            loader = TextLoader(file_path)
        elif file_extension == '.pdf':
            loader = PyPDFLoader(file_path)
        elif file_extension in ['.docx', '.doc']:
            loader = UnstructuredFileLoader(file_path)
        else:
            logger.error(f"Unsupported file format: {file_extension}")
            return None
            
        # Extract and combine text from all pages
        docs = loader.load()
        text_content = "\n".join(doc.page_content for doc in docs)
        
        if text_content and len(text_content.strip()) > 0:
            logger.info(f"Successfully extracted {len(text_content)} characters from {file_name}")
            return text_content
        else:
            logger.warning(f"Extracted empty text content from {file_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error reading CV file {file_path}: {e}")
        return None
    

async def extract_text_from_uploaded_file(uploaded_file) -> Optional[str]:
    """
    Extract text from a file uploaded through Streamlit
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        str: Extracted text content, or None if extraction failed
    """
    try:
        # Create a temporary file to process with LangChain loaders
        temp_path = os.path.join(CV_DATA_DIR, f"temp_{uuid.uuid4()}{Path(uploaded_file.name).suffix}")
        
        # Write the uploaded file to a temporary location
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Use the existing read_cv_text function to extract text
        text_content = await read_cv_text(temp_path)
        
        # Clean up the temporary file
        os.remove(temp_path)
        
        return text_content
            
    except Exception as e:
        logger.error(f"Error extracting text from uploaded file {uploaded_file.name}: {e}")
        return None