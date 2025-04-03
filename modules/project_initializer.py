#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from datetime import datetime
import time
import logging

def create_project_folder() -> str:
    """
    Creates a new project folder
    
    Returns:
        str: The full path of the created folder
    """
    # Get logger
    logger = logging.getLogger("merak_makinesi")
    
    # Use current time without seconds to avoid too granular folders 
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Validate timestamp format - make sure it's current year or at worst next year
        # This catches system clock issues
        year = int(timestamp[:4])
        current_year = time.localtime().tm_year
        
        if year > current_year + 1 or year < current_year - 1:
            logger.warning(f"System date may be incorrect: {timestamp}, using safer format")
            # Use safer format with hours-minutes only
            timestamp = f"{current_year}-{time.localtime().tm_mon:02d}-{time.localtime().tm_mday:02d}_{time.localtime().tm_hour:02d}-{time.localtime().tm_min:02d}"
    except Exception as e:
        logger.error(f"Error creating timestamp: {str(e)}")
        # Fallback using epoch time
        timestamp = f"video_{int(time.time())}"
    
    # Ensure output directory exists
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    project_folder = os.path.join(output_dir, f"video_{timestamp}")
    
    # Create main folder
    try:
        os.makedirs(project_folder, exist_ok=True)
        logger.info(f"Created project folder: {project_folder}")
    except Exception as e:
        logger.error(f"Error creating project folder: {str(e)}")
        # Fallback to a simpler name if there's an error
        project_folder = os.path.join(output_dir, f"video_{int(time.time())}")
        os.makedirs(project_folder, exist_ok=True)
        logger.info(f"Using fallback project folder: {project_folder}")
    
    # Create subfolders with error handling
    try:
        os.makedirs(os.path.join(project_folder, "pexels_videos"), exist_ok=True)
        os.makedirs(os.path.join(project_folder, "tts_audio"), exist_ok=True)
    except Exception as e:
        logger.warning(f"Error creating subfolders: {str(e)}")
    
    # Create empty files with error handling
    try:
        with open(os.path.join(project_folder, "metadata.json"), "w", encoding="utf-8") as f:
            f.write("""{"creation_time": "%s", "status": "initialized"}""" % datetime.now().isoformat())
    except Exception as e:
        logger.warning(f"Error creating metadata.json: {str(e)}")
    
    try:
        with open(os.path.join(project_folder, "error_log.txt"), "w", encoding="utf-8") as f:
            f.write(f"Project initialized at {datetime.now().isoformat()}\n")
    except Exception as e:
        logger.warning(f"Error creating error_log.txt: {str(e)}")
    
    return project_folder 