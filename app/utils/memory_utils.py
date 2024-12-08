"""Memory usage monitoring utilities"""
import os
import psutil
import logging

logger = logging.getLogger(__name__)

def log_memory_usage():
    """Log current memory usage and return usage in MB"""
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
        logger.info(f"Current memory usage: {memory_mb:.2f} MB")
        return memory_mb
    except Exception as e:
        logger.error(f"Error getting memory usage: {str(e)}")
        return 0

def optimize_memory():
    """Attempt to optimize memory usage"""
    try:
        import gc
        gc.collect()
        logger.info("Memory optimization completed")
    except Exception as e:
        logger.error(f"Error optimizing memory: {str(e)}")