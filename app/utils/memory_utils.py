import os
import psutil
import gc
import logging

logger = logging.getLogger(__name__)

def check_memory_usage():
    """Monitor memory usage"""
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_usage = memory_info.rss / 1024 / 1024  # Convert to MB
        logger.info(f"Current memory usage: {memory_usage:.2f} MB")
        return memory_usage
    except Exception as e:
        logger.error(f"Error checking memory usage: {str(e)}")
        return None

def optimize_memory():
    """Optimize memory usage"""
    try:
        initial_memory = check_memory_usage()
        gc.collect()
        final_memory = check_memory_usage()
        if initial_memory and final_memory:
            logger.info(f"Memory optimized: {initial_memory - final_memory:.2f} MB freed")
    except Exception as e:
        logger.error(f"Error optimizing memory: {str(e)}")

def log_memory_usage(app):
    """Log current memory usage to Flask app logger"""
    memory_usage = check_memory_usage()
    if memory_usage:
        app.logger.info(f"Current memory usage: {memory_usage:.2f} MB")