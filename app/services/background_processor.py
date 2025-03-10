import asyncio
import logging
import os
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

from app.services.data_extraction_service import DataExtractionService
from app.services.neo4j_service import Neo4jService
from app.utils.file_utils import read_cv_text

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CVProcessorService:

    data_extraction_service: DataExtractionService
    neo4j_service: Neo4jService

    """Service to process CVs in the background using a thread pool and queue system"""
    
    def __init__(self, max_workers=None):
        """Initialize the CV processor service with a thread pool
        
        Args:
            max_workers (int, optional): Maximum number of worker threads. Defaults to CPU count * 3.
        """
        self.data_extraction_service = DataExtractionService()
        self.neo4j_service = Neo4jService()
        self.is_processing = False
        self.cv_queue = queue.Queue()
        # Default to CPU count * 3 with a maximum of 32, but allow override
        self.max_workers = max_workers if max_workers is not None else min(32, os.cpu_count() * 3)
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self._shutdown_event = threading.Event()
        
    def add_cv_to_queue(self, original_filename: str, unique_filename: str, file_path: str) -> None:
        """Add a CV to the processing queue
        
        Args:
            original_filename (str): Original filename of the CV
            unique_filename (str): Unique filename for storage
            file_path (str): Path to the saved CV file
        """
        self.cv_queue.put((original_filename, unique_filename, file_path))
        logger.info(f"Added CV to queue: {original_filename} (as {unique_filename})")
    
    def get_queue_size(self) -> int:
        """Get the current size of the CV processing queue
        
        Returns:
            int: Number of CVs waiting to be processed
        """
        return self.cv_queue.qsize()
    
    async def start_background_processing(self) -> None:
        """Start background processing of CVs from the queue"""
        if self.is_processing:
            logger.info("Background processing is already running")
            return
            
        logger.info(f"Starting background CV processing with {self.max_workers} workers")
        self.is_processing = True
        self._shutdown_event.clear()
        
        # Create a semaphore to limit concurrent tasks
        semaphore = asyncio.Semaphore(self.max_workers)
        tasks = []
        
        # Process CVs from the queue until stopped
        while not self._shutdown_event.is_set():
            try:
                # Try to get a CV from the queue with timeout
                try:
                    original_filename, unique_filename, file_path = self.cv_queue.get(timeout=1)
                except queue.Empty:
                    # Queue is empty, wait a bit and check again
                    await asyncio.sleep(0.5)
                    continue
                
                # Process this CV with concurrency control
                async def process_with_semaphore():
                    async with semaphore:
                        return await self.process_cv(file_path, unique_filename, original_filename)
                
                task = asyncio.create_task(process_with_semaphore())
                tasks.append(task)
                
                # Mark task as done in the queue
                self.cv_queue.task_done()
                
                # Clean up completed tasks
                tasks = [t for t in tasks if not t.done()]
                
            except Exception as e:
                logger.error(f"Error in background processing: {e}")
                await asyncio.sleep(1)  # Pause briefly if there's an error
        
        # Wait for all remaining tasks to complete
        if tasks:
            logger.info(f"Waiting for {len(tasks)} remaining tasks to complete")
            await asyncio.gather(*tasks, return_exceptions=True)
            
        self.is_processing = False
        logger.info("Background CV processing stopped")
    
    async def stop_background_processing(self) -> None:
        """Stop background processing"""
        if not self.is_processing:
            logger.info("Background processing is not running")
            return
            
        logger.info("Stopping background CV processing")
        self._shutdown_event.set()
        
        # Wait for up to 5 seconds for processing to stop
        for _ in range(10):
            if not self.is_processing:
                break
            await asyncio.sleep(0.5)
    
    async def process_cv(self, cv_path: str, cv_filename: str, original_filename: str = None) -> bool:
        """
        Process a single CV file
        
        Args:
            cv_path (str): The path to the CV file
            cv_filename (str): The unique filename for storage
            original_filename (str, optional): Original filename of the CV
            
        Returns:
            bool: True if processed successfully, False otherwise
        """
        try:
            display_name = original_filename or cv_filename
            logger.info(f"Processing CV: {display_name}")
            
            # Read CV text from file
            cv_text = await read_cv_text(cv_path)
            if not cv_text:
                logger.error(f"Failed to read text from CV: {display_name}")
                return False
                
            # Extract structured data from CV
            cv_data = await self.data_extraction_service.extract_cv_data(cv_text, cv_filename)
            
            # Store data in Neo4j database
            if cv_data and isinstance(cv_data, dict) and cv_data.get("person"):
                # Store person data
                person = cv_data.get("person")
                person_id = await self.neo4j_service.create_person_node(person)
                
                # Store experiences
                if cv_data.get("experiences") and cv_data["experiences"].experiences:
                    for exp in cv_data["experiences"].experiences:
                        await self.neo4j_service.create_experience_relationship(person_id, exp)
                
                # Store skills
                if cv_data.get("skills") and cv_data["skills"].skills:
                    for skill in cv_data["skills"].skills:
                        await self.neo4j_service.create_skill_relationship(person_id, skill)
                
                logger.info(f"Successfully processed and stored CV: {display_name}")
                return True
            else:
                logger.error(f"Failed to extract data from CV: {display_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing CV {display_name}: {e}", exc_info=True)
            return False