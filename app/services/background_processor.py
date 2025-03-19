import logging
import os
import queue
import asyncio
from typing import Dict, List, Optional, Tuple, Any

from app.services.data_extraction_service import DataExtractionService
from app.services.neo4j_service import Neo4jService
from app.utils.file_utils import read_cv_text

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CVProcessorService:
    """Service to process CVs sequentially using a simple queue system"""
    
    def __init__(self):
        """Initialize the CV processor service"""
        self.data_extraction_service = DataExtractionService()
        self.neo4j_service = Neo4jService()
        self.is_processing = False
        self.cv_queue = queue.Queue()
    
    def start(self) -> None:
        """Mark the service as started"""
        self.is_processing = True
        logger.info("CV processor service started")
        
    def is_alive(self) -> bool:
        """Check if service is running"""
        return self.is_processing
    
    def add_cv_to_queue(self, original_filename: str, unique_filename: str, file_path: str) -> None:
        """Add a CV to the processing queue"""
        self.cv_queue.put((original_filename, unique_filename, file_path))
        logger.info(f"Added CV to queue: {original_filename} (as {unique_filename})")
        
        # Auto-start if not already running
        if not self.is_processing:
            self.start()
    
    def get_queue_size(self) -> int:
        """Get the current size of the CV processing queue"""
        return self.cv_queue.qsize()
    
    async def process_next_cv(self) -> bool:
        """Process the next CV in the queue
        
        Returns:
            bool: True if a CV was processed, False if queue was empty
        """
        if not self.is_processing:
            logger.warning("Cannot process CV: processor is not running")
            return False
            
        try:
            # Try to get a CV from the queue with a timeout
            original_filename, unique_filename, file_path = self.cv_queue.get(block=False)
            
            try:
                success = await self.process_cv(file_path, unique_filename, original_filename)
                return success
            except Exception as e:
                logger.error(f"Error processing CV: {e}", exc_info=True)
                return False
            finally:
                # Mark the task as done in the queue
                self.cv_queue.task_done()
                
        except queue.Empty:
            # Queue is empty, nothing to process
            return False
        
    def process_all_cvs(self):
        """
        Process all CVs in the queue synchronously (wraps async operation)
        
        Returns:
            Number of processed CVs
        """
        # Create a new event loop for this thread if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async method in the event loop
        return loop.run_until_complete(self._process_all_cvs_async())
    
    async def _process_all_cvs_async(self):
        """
        Process all CVs in the queue (async implementation)
        
        Returns:
            Number of processed CVs
        """
        processed = 0
        while not self.cv_queue.empty():
            try:
                original_filename, unique_filename, file_path = self.cv_queue.get_nowait()
                success = await self.process_cv(file_path, unique_filename, original_filename)
                if success:
                    processed += 1
            except Exception as e:
                logger.error(f"Error in process_all_cvs: {e}")
            finally:
                self.cv_queue.task_done()
        
        return processed
    
    async def process_cv(self, cv_path: str, cv_filename: str, original_filename: Optional[str] = None) -> bool:
        """Process a single CV file"""
        try:
            display_name = original_filename or cv_filename
            logger.info(f"Processing CV: {display_name}")
            
            # Read CV text - simple synchronous version
            cv_text = await read_cv_text(cv_path)
            if not cv_text:
                logger.error(f"Failed to read text from CV: {display_name}")
                return False
            
            # Extract structured data from CV
            # Note: This assumes extract_cv_data has a synchronous version
            cv_data = await self.data_extraction_service.extract_cv_data(cv_text, cv_filename)
            logger.info(f"The extraction is successful. Data: {cv_data}")
            
            # Generate a unique candidate ID based on filename
            candidate_id = os.path.splitext(cv_filename)[0]
            logger.info(f"Generated candidate ID: {candidate_id}")
            
            # Add candidate to Neo4j
            success = self.neo4j_service.add_candidate(
                candidate_id=candidate_id,
                person_data=cv_data['person'],
                experiences=cv_data['experiences'],
                skills=cv_data['skills']
            )
            
            if success:
                logger.info(f"Successfully added candidate {cv_filename} to Neo4j")
            else:
                logger.error(f"Failed to add candidate {cv_filename} to Neo4j")
            
            return success
                
        except Exception as e:
            logger.error(f"Error processing CV {display_name}: {e}", exc_info=True)
            return False
    
    def shutdown(self) -> None:
        """Stop the processor service"""
        self.is_processing = False
        logger.info("CV processor service stopped")