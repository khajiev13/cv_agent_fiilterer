import os
import logging
import uuid
from pathlib import Path
from datetime import datetime
import asyncio
import subprocess
from typing import Optional
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
    Read text from a CV file (PDF, DOCX, DOC, or TXT)
    
    Args:
        file_path: Path to the CV file
        
    Returns:
        str: Extracted text content, or None if extraction failed
    """
    try:
        file_name = os.path.basename(file_path)
        file_extension = Path(file_path).suffix.lower()
        
        # Read file bytes
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
            
        text_content = None
        
        if file_extension == '.txt':
            # Handle text files
            text_content = file_bytes.decode('utf-8')
            
        elif file_extension == '.pdf':
            # Try pdfplumber first (better handling of layouts)
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                    text_content = "\n".join([page.extract_text() or "" for page in pdf.pages])
            except ImportError:
                logger.info("pdfplumber not available, falling back to alternatives")
                # Try pdftotext command line tool next
                try:
                    result = subprocess.run(['pdftotext', file_path, '-'], 
                                           capture_output=True, 
                                           text=True, 
                                           check=True)
                    text_content = result.stdout
                except (subprocess.SubprocessError, FileNotFoundError):
                    # Finally try PyPDF2
                    try:
                        import PyPDF2
                        with open(file_path, 'rb') as file:
                            reader = PyPDF2.PdfReader(file)
                            text_content = ""
                            for page_num in range(len(reader.pages)):
                                text_content += reader.pages[page_num].extract_text() or ""
                    except Exception as e:
                        logger.error(f"All PDF extraction methods failed: {e}")
            except Exception as e:
                logger.error(f"Error in pdfplumber: {e}")
                
        elif file_extension == '.docx':
            # Use python-docx for DOCX
            try:
                import docx
                doc = docx.Document(io.BytesIO(file_bytes))
                text_content = "\n".join([para.text for para in doc.paragraphs])
            except Exception as e:
                logger.error(f"Error extracting text from DOCX: {e}")
                
        elif file_extension == '.doc':
            # Try textract for DOC files (legacy format)
            try:
                import textract
                # Save file temporarily to process with textract
                temp_path = f"/tmp/{file_name}"
                with open(temp_path, "wb") as f:
                    f.write(file_bytes)
                text_content = textract.process(temp_path).decode('utf-8')
                os.remove(temp_path)  # Clean up temp file
            except ImportError:
                logger.warning("textract not installed. DOC files may not be processed correctly.")
                logger.info("Install textract with: pip install textract")
                # Try antiword as fallback
                try:
                    result = subprocess.run(['antiword', file_path], 
                                           capture_output=True, 
                                           text=True)
                    text_content = result.stdout
                except (subprocess.SubprocessError, FileNotFoundError):
                    logger.error("Could not extract text from DOC file - neither textract nor antiword available")
            except Exception as e:
                logger.error(f"Error extracting text from DOC: {e}")
        else:
            logger.error(f"Unsupported file format: {file_extension}")
            
        # Return extracted content or None
        if text_content and len(text_content.strip()) > 0:
            logger.info(f"Successfully extracted {len(text_content)} characters from {file_name}")
            return text_content
        else:
            logger.warning(f"Extracted empty text content from {file_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error reading CV file {file_path}: {e}")
        return None