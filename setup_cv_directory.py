import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_directories():
    """
    Create necessary directories for the application if they don't exist
    """
    # Define the directories needed
    directories = [
        "data",
        "data/cvs",
        "data/temp"
    ]
    
    # Create each directory if it doesn't exist
    for directory in directories:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                logger.info(f"Created directory: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")
    
    logger.info("Directory setup complete")
    
    # Return success status
    return all(os.path.exists(directory) for directory in directories)

if __name__ == "__main__":
    print("Setting up Resume Agent directories...")
    success = setup_directories()
    if success:
        print("✓ Setup completed successfully!")
        print("  The following directories have been verified:")
        print("  - data/cvs (for CV storage)")
        print("  - data/temp (for temporary files)")
    else:
        print("⚠ Setup encountered some issues. Check the logs for details.")
