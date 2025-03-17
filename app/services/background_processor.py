import logging
import os
import queue
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple, Any

from app.services.data_extraction_service import DataExtractionService
from app.services.neo4j_service import Neo4jService
from app.utils.file_utils import read_cv_text

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CVProcessorService(threading.Thread):
    """Service to process CVs in the background using a thread pool and queue system"""
    
    def __init__(self, max_workers: Optional[int] = None):
        """Initialize the CV processor service with a thread pool
        
        Args:
            max_workers: Maximum number of worker threads. Defaults to CPU count * 3.
        """
        super().__init__(daemon=True)  # Initialize as daemon thread
        self.data_extraction_service: DataExtractionService = DataExtractionService()
        self.neo4j_service: Neo4jService = Neo4jService()
        self.is_processing: bool = False
        self.cv_queue: queue.Queue = queue.Queue()
        # Default to CPU count * 3 with a maximum of 32, but allow override
        self.max_workers: int = max_workers if max_workers is not None else min(32, os.cpu_count() or 4)
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=self.max_workers)
        self._shutdown_event: threading.Event = threading.Event()
        
    def run(self) -> None:
        """Main processing loop that continuously processes CVs from the queue"""
        self.is_processing = True
        logger.info("CV processor thread started")
        
        while not self._shutdown_event.is_set():
            try:
                # Try to get a CV from the queue with a timeout
                # This allows checking the shutdown event periodically
                original_filename, unique_filename, file_path = self.cv_queue.get(timeout=1.0)
                
                try:
                    # Process the CV using the executor's thread pool
                    future = self.executor.submit(
                        self.process_cv, file_path, unique_filename, original_filename
                    )
                    # We could add callbacks here if needed
                except Exception as e:
                    logger.error(f"Error submitting job to executor: {e}", exc_info=True)
                finally:
                    # Mark the task as done in the queue
                    self.cv_queue.task_done()
                    
            except queue.Empty:
                # Queue timeout - no items available, continue loop
                pass
            except Exception as e:
                logger.error(f"Error in processing thread: {e}", exc_info=True)
        
        # Clean up when exiting the loop
        self.is_processing = False
        logger.info("CV processor thread stopped")
        
    def shutdown(self) -> None:
        """Signal the processing thread to stop and clean up resources"""
        if self.is_processing:
            logger.info("Shutting down CV processor...")
            self._shutdown_event.set()
            if self.is_alive():
                self.join(timeout=30)  # Wait up to 30 seconds for thread to finish
            self.executor.shutdown(wait=True)
            logger.info("CV processor has been shut down")
            
    def add_cv_to_queue(self, original_filename: str, unique_filename: str, file_path: str) -> None:
        """Add a CV to the processing queue
        
        Args:
            original_filename: Original filename of the CV
            unique_filename: Unique filename for storage
            file_path: Path to the saved CV file
        """
        self.cv_queue.put((original_filename, unique_filename, file_path))
        logger.info(f"Added CV to queue: {original_filename} (as {unique_filename})")
        
        # Auto-start the processing thread if not already running
        if not self.is_processing and not self.is_alive():
            self.start()
    
    def get_queue_size(self) -> int:
        """Get the current size of the CV processing queue
        
        Returns:
            Number of CVs waiting to be processed
        """
        return self.cv_queue.qsize()
    
    def process_cv(self, cv_path: str, cv_filename: str, original_filename: Optional[str] = None) -> bool:
        """Process a single CV file
        
        Args:
            cv_path: The path to the CV file
            cv_filename: The unique filename for storage
            original_filename: Original filename of the CV
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            display_name = original_filename or cv_filename
            logger.info(f"Processing CV: {display_name}")
            
            
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Read CV text
                if asyncio.iscoroutinefunction(read_cv_text):
                    cv_text = loop.run_until_complete(read_cv_text(cv_path))
                else:
                    cv_text = read_cv_text(cv_path)
                
                if not cv_text:
                    logger.error(f"Failed to read text from CV: {display_name}")
                    return False
                
                # Extract structured data from CV
                cv_data = loop.run_until_complete(
                    self.data_extraction_service.extract_cv_data(cv_text, cv_filename)
                )
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
            finally:
                # Clean up resources
                loop.close()
                
        except Exception as e:
            logger.error(f"Error processing CV {display_name}: {e}", exc_info=True)
            return False