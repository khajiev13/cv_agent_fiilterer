import asyncio
import logging
import os
from app.services.data_extraction_service import DataExtractionService
from app.services.neo4j_service import Neo4jService
from app.utils.file_utils import read_cv_text
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CVProcessorService:
    def __init__(self):
        """Initialize the CV processor service"""
        self.data_extraction_service = DataExtractionService()
        self.neo4j_service = Neo4jService()
        self.is_processing = False
    
    async def process_cv(self, cv_path, cv_filename):
        """
        Process a single CV file
        
        Args:
            cv_path (str): The path to the CV file
            cv_filename (str): The filename of the CV
            
        Returns:
            bool: True if processed successfully, False otherwise
        """
        try:
            logger.info(f"Processing CV: {cv_filename}")
            
            # Read CV text from file
            cv_text = await read_cv_text(cv_path)
            if not cv_text:
                logger.error(f"Failed to read text from CV: {cv_filename}")
                return False
                
            # Extract structured data from CV
            cv_data = await self.data_extraction_service.extract_cv_data(cv_text, cv_filename)
            
            # Insert data into Neo4j
            success = self.neo4j_service.insert_cv_data(cv_data, cv_filename)
            
            if success:
                # Update extraction status in Neo4j
                self.neo4j_service.update_cv_extraction_status(cv_filename, True)
                logger.info(f"Successfully processed CV: {cv_filename}")
                return True
            else:
                logger.error(f"Failed to insert CV data for: {cv_filename}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing CV {cv_filename}: {e}")
            return False
    
    async def process_all_unextracted_cvs(self):
        """
        Process all unextracted CVs from Neo4j
        
        Returns:
            int: Number of CVs successfully processed
        """
        
        if self.is_processing:
            logger.info("CV processing already in progress")
            return 0
            
        self.is_processing = True
        try:
            # Get all unextracted CVs
            cv_filenames = self.neo4j_service.get_unextracted_cvs()
            
            if not cv_filenames:
                logger.info("No unextracted CVs found")
                return 0
                
            logger.info(f"Found {len(cv_filenames)} unextracted CVs")
            
            # Get the upload directory from environment or use default
            # Change this to the correct path
            upload_dir = os.getenv("UPLOAD_DIR", "data/cvs")
            
            # Process each CV
            success_count = 0
            tasks = []
            
            for filename in cv_filenames:
                file_path = os.path.join(upload_dir, filename)
                # Check if file exists at this path
                if os.path.exists(file_path):
                    tasks.append(self.process_cv(file_path, filename))
                else:
                    logger.warning(f"CV file not found: {file_path}")
                    # Try alternative paths if primary location fails
                    alternative_paths = [
                        os.path.join("uploads", filename),
                        os.path.join("data", "cvs", filename),
                        os.path.join("app", "data", "cvs", filename)
                    ]
                    
                    file_found = False
                    for alt_path in alternative_paths:
                        if os.path.exists(alt_path):
                            logger.info(f"Found CV at alternative path: {alt_path}")
                            tasks.append(self.process_cv(alt_path, filename))
                            file_found = True
                            break
                    
                    if not file_found:
                        logger.error(f"CV file {filename} not found in any expected location")
            
            # Process all CVs concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful extractions
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Task exception: {result}")
                elif result is True:
                    success_count += 1
            
            logger.info(f"Processed {success_count} of {len(cv_filenames)} CVs")
            return success_count
            
        except Exception as e:
            logger.error(f"Error in batch CV processing: {e}")
            return 0
        finally:
            self.is_processing = False
            
    async def start_background_processing(self):
        """Start background processing of unextracted CVs"""
        logger.info("Starting background CV processing")
        await self.process_all_unextracted_cvs()