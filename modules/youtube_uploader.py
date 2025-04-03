#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import subprocess
import shutil
import logging
import glob
from datetime import datetime
from glob import glob

class YouTubeUploader:
    """Class that uses the Node.js MMotoYT application to upload videos to YouTube"""
    
    def __init__(self):
        """
        Initializes the YouTube uploader class
        """
        self.mmoto_yt_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "MMotoYT")
        self.logger = logging.getLogger("merak_makinesi")
        
        # Verify MMotoYT directory exists
        if not os.path.exists(self.mmoto_yt_dir):
            self.logger.warning(f"MMotoYT directory not found at: {self.mmoto_yt_dir}")
            # Try to find it in a different location
            alt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "MMotoYT")
            if os.path.exists(alt_path):
                self.mmoto_yt_dir = os.path.abspath(alt_path)
                self.logger.info(f"Found MMotoYT at alternative location: {self.mmoto_yt_dir}")
    
    def authenticate(self):
        """
        Authenticates with the YouTube API - MMotoYT application does this automatically
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        # Check if MMotoYT directory exists
        if not os.path.exists(self.mmoto_yt_dir):
            self.logger.error(f"MMotoYT directory not found: {self.mmoto_yt_dir}")
            return False
            
        # Check if tokens.json file exists
        tokens_path = os.path.join(self.mmoto_yt_dir, "tokens.json")
        return os.path.exists(tokens_path)
    
    def upload_video(self, video_path, title, description, tags=None, category="27", 
                    privacy_status="public", is_shorts=True, notify_subscribers=True):
        """
        Uploads a video to YouTube
        
        Args:
            video_path (str): Path to the video file to upload
            title (str): Video title
            description (str): Video description
            tags (list): Video tags
            category (str): Video category ID
            privacy_status (str): Privacy status (public, private, unlisted)
            is_shorts (bool): True if the video should be uploaded as a Short
            notify_subscribers (bool): True if subscribers should be notified
        
        Returns:
            dict: Upload result information
        """
        # Validate video path
        if not os.path.exists(video_path):
            self.logger.error(f"Video file not found: {video_path}")
            
            # Try to find the video in the parent directory
            video_dir = os.path.dirname(video_path)
            if os.path.exists(video_dir):
                mp4_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
                if mp4_files:
                    new_video_path = os.path.join(video_dir, mp4_files[0])
                    self.logger.info(f"Found alternative video file: {new_video_path}")
                    video_path = new_video_path
                else:
                    self.logger.error(f"No MP4 files found in directory: {video_dir}")
                    return {"success": False, "error": f"Video file not found: {video_path} and no alternatives found"}
            else:
                return {"success": False, "error": f"Video file not found: {video_path}"}
        
        # Validate MMotoYT directory
        if not os.path.exists(self.mmoto_yt_dir):
            self.logger.error(f"MMotoYT directory not found: {self.mmoto_yt_dir}")
            return {"success": False, "error": f"MMotoYT directory not found: {self.mmoto_yt_dir}"}
            
        try:
            # Ensure description is not None
            if not description:
                description = f"Video about {title}" 
                
            # Ensure title is not None
            if not title:
                title = f"Video {datetime.now().strftime('%Y-%m-%d')}"
            
            # Validate input types
            title = str(title)
            description = str(description)
            if not isinstance(tags, list):
                if tags:
                    tags = [str(tags)]
                else:
                    tags = []
            else:
                tags = [str(tag) for tag in tags]
                
            # Create JSON metadata file for the video
            # MMotoYT expects a JSON file with the same name as the video
            try:
                # Create a link/copy to the video file in the MMotoYT videos directory
                videos_dir = os.path.join(self.mmoto_yt_dir, "videos")
                os.makedirs(videos_dir, exist_ok=True)
                
                # Copy video file to MMotoYT videos directory
                video_filename = os.path.basename(video_path)
                mmoto_video_path = os.path.join(videos_dir, video_filename)
                
                # Copy the file if it doesn't exist in the target location
                if not os.path.exists(mmoto_video_path):
                    self.logger.info(f"Copying video to MMotoYT videos directory: {mmoto_video_path}")
                    shutil.copy2(video_path, mmoto_video_path)
                
                # Create metadata file
                metadata = {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": category,
                    "privacyStatus": privacy_status
                }
                
                metadata_path = mmoto_video_path + ".json"
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                    
                self.logger.info(f"Created metadata file for MMotoYT: {metadata_path}")
            except Exception as e:
                self.logger.warning(f"Error preparing video for MMotoYT: {str(e)}")
                # Continue anyway, MMotoYT might be able to process the video directly
            
            # Change to MMotoYT directory
            original_dir = os.getcwd()
            os.chdir(self.mmoto_yt_dir)
            
            # Run MMotoYT application 
            self.logger.info("Starting MMotoYT application...")
            print("Running MMotoYT to upload the video...")
            
            try:
                # First try to directly use node to run index.js
                index_js_path = os.path.join(self.mmoto_yt_dir, "index.js")
                
                if os.path.exists(index_js_path):
                    self.logger.info("Using node index.js to start MMotoYT")
                    
                    # For Windows, we need to use shell=True and full command
                    if os.name == 'nt':  # Windows
                        process = subprocess.Popen(
                            "node index.js",
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            encoding='utf-8',  # Explicitly set encoding to UTF-8
                            cwd=self.mmoto_yt_dir
                        )
                    else:  # Unix
                        process = subprocess.Popen(
                            ["node", "index.js"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            encoding='utf-8',  # Explicitly set encoding to UTF-8
                            cwd=self.mmoto_yt_dir
                        )
                        
                    self.logger.info(f"MMotoYT process started with PID: {process.pid}")
                    
                    # Set a reasonable timeout (3 minutes)
                    timeout = 180
                    start_time = time.time()
                    
                    # Wait for the process to complete or timeout
                    output_lines = []
                    error_lines = []
                    
                    while process.poll() is None and time.time() - start_time < timeout:
                        # Read output line by line with timeout
                        stdout_line = process.stdout.readline()
                        if stdout_line:
                            output_lines.append(stdout_line.strip())
                            print(f"MMotoYT: {stdout_line.strip()}")
                        
                        # Read error lines as well
                        stderr_line = process.stderr.readline()
                        if stderr_line:
                            error_lines.append(stderr_line.strip())
                            print(f"MMotoYT Error: {stderr_line.strip()}")
                        
                        # Small sleep to avoid CPU hogging
                        time.sleep(0.1)
                    
                    # Check if timed out
                    if process.poll() is None:
                        self.logger.warning(f"MMotoYT process timed out after {timeout} seconds")
                        process.terminate()
                        try:
                            process.wait(timeout=5)  # Give it 5 seconds to terminate
                        except subprocess.TimeoutExpired:
                            process.kill()  # Force kill if still running
                            
                        output = "\n".join(output_lines)
                        errors = "\n".join(error_lines)
                    else:
                        # Get any remaining output
                        stdout, stderr = process.communicate()
                        if stdout:
                            output_lines.append(stdout)
                        if stderr:
                            error_lines.append(stderr)
                            
                        output = "\n".join(output_lines)
                        errors = "\n".join(error_lines)
                        
                        self.logger.info(f"MMotoYT process completed with exit code: {process.returncode}")
                    
                    # Create a simulated result object
                    result = type('Result', (), {
                        'returncode': process.returncode if process.poll() is not None else 1,
                        'stdout': output,
                        'stderr': errors
                    })
                else:
                    # Run batch file as a fallback
                    run_bat_path = os.path.join(self.mmoto_yt_dir, "run.bat")
                    if os.path.exists(run_bat_path):
                        self.logger.info("Using run.bat to start MMotoYT")
                        
                        # For Windows, create a process that will complete even if the batch file launches other processes
                        process = subprocess.Popen(
                            "run.bat",
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            encoding='utf-8',  # Explicitly set encoding to UTF-8
                            cwd=self.mmoto_yt_dir
                        )
                        
                        # Wait for a short time for immediate output
                        time.sleep(5)
                        
                        # Don't wait for it to finish, just check if it started successfully
                        if process.poll() is None:
                            # Still running, which is good for a batch file
                            self.logger.info("Batch file started successfully")
                            
                            # Create a simulated successful result
                            result = type('Result', (), {
                                'returncode': 0,
                                'stdout': "Batch file execution started",
                                'stderr': ""
                            })
                        else:
                            # Completed too quickly, might be an error
                            stdout, stderr = process.communicate()
                            self.logger.warning(f"Batch file completed too quickly with code {process.returncode}")
                            
                            result = type('Result', (), {
                                'returncode': process.returncode,
                                'stdout': stdout,
                                'stderr': stderr
                            })
                    else:
                        self.logger.error("Cannot find run.bat or index.js in MMotoYT directory")
                        return {"success": False, "error": "MMotoYT startup files not found"}
                
                # Process the result
                if result.returncode == 0:
                    # Successful exit or started successfully
                    output = result.stdout
                    
                    # Extract Video ID and URL from output
                    video_id = None
                    video_url = None
                    
                    for line in output.split("\n"):
                        if "Video ID:" in line:
                            video_id = line.split("Video ID:")[1].strip()
                        elif "Video URL:" in line:
                            video_url = line.split("Video URL:")[1].strip()
                    
                    if video_id:
                        self.logger.info(f"Video successfully uploaded: {video_url}")
                        
                        # Return result
                        return {
                            "success": True,
                            "video_id": video_id,
                            "video_url": video_url,
                            "shorts_url": f"https://youtube.com/shorts/{video_id}" if is_shorts else None
                        }
                    else:
                        # Check uploaded.txt files in output folders
                        output_dir = os.path.join(os.path.dirname(self.mmoto_yt_dir), "output")
                        
                        # Find the project directory based on the video path
                        project_dir = os.path.dirname(video_path)
                        upload_mark = os.path.join(project_dir, "uploaded.txt")
                        
                        if os.path.exists(upload_mark):
                            self.logger.info(f"Found upload mark in video directory: {project_dir}")
                            try:
                                with open(upload_mark, 'r') as f:
                                    content = f.read()
                                
                                # Extract video ID and URL
                                for line in content.split('\n'):
                                    if "Video ID:" in line:
                                        video_id = line.split("Video ID:")[1].strip()
                                    elif "Video URL:" in line:
                                        video_url = line.split("Video URL:")[1].strip()
                                
                                if video_id:
                                    return {
                                        "success": True,
                                        "video_id": video_id,
                                        "video_url": video_url,
                                        "shorts_url": f"https://youtube.com/shorts/{video_id}" if is_shorts else None
                                    }
                            except Exception as e:
                                self.logger.warning(f"Error reading uploaded.txt: {str(e)}")
                        
                        # Create an upload marker in the video directory anyway
                        try:
                            with open(upload_mark, 'w') as f:
                                f.write(f"Uploaded on: {datetime.now().isoformat()}\n")
                                f.write("Status: Attempted upload but couldn't confirm\n")
                        except Exception as e:
                            self.logger.warning(f"Error creating upload marker: {str(e)}")
                        
                        # If no video ID found, return success message
                        message = "Upload process initiated, but could not confirm video ID. Please check YouTube for the video."
                        self.logger.info(message)
                        return {"success": True, "message": message, "video_id": None, "video_url": None}
                else:
                    # MMotoYT error
                    error_message = "Unknown error"
                    if hasattr(result, 'stderr') and result.stderr:
                        error_message = result.stderr
                    self.logger.error(f"MMotoYT error: {error_message}")
                    return {"success": False, "error": error_message}
                
            except Exception as e:
                self.logger.error(f"Error during upload process: {str(e)}")
                return {"success": False, "error": str(e)}
            finally:
                # Return to original working directory
                os.chdir(original_dir)
                
                # Make sure all child processes are killed
                if 'process' in locals() and process and process.poll() is None:
                    try:
                        process.terminate()
                        process.wait(timeout=5)  # Give it 5 seconds to terminate
                    except:
                        try:
                            process.kill()  # Force kill
                        except:
                            pass  # Ignore errors during cleanup
            
        except Exception as e:
            self.logger.error(f"Video upload error: {str(e)}")
            return {"success": False, "error": str(e)}

# Direct execution test
if __name__ == "__main__":
    # Test code
    # Upload the last generated video to YouTube
    uploader = YouTubeUploader()
    
    # Find the last generated video directory
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(root_dir, "output")
    
    if not os.path.exists(output_dir):
        print(f"Output directory not found: {output_dir}")
        exit(1)
        
    output_dirs = sorted(glob(os.path.join(output_dir, "video_*")), key=os.path.getmtime)
    
    if output_dirs:
        last_output_dir = output_dirs[-1]
        video_path = os.path.join(last_output_dir, "final_video.mp4")
        
        # If final_video.mp4 doesn't exist, look for any mp4 file
        if not os.path.exists(video_path):
            mp4_files = glob(os.path.join(last_output_dir, "*.mp4"))
            if mp4_files:
                video_path = mp4_files[0]
                print(f"Using alternative video file: {os.path.basename(video_path)}")
            else:
                print(f"No video files found in {last_output_dir}")
                exit(1)
        
        # Read metadata file
        metadata_path = os.path.join(last_output_dir, "metadata.json")
        metadata = None
        
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except Exception as e:
                print(f"Error reading metadata file: {str(e)}")
                metadata = {
                    "title": f"Video {datetime.now().strftime('%Y-%m-%d')}",
                    "content": "Automatically generated video",
                    "keywords": ["educational", "shorts", "facts"]
                }
        else:
            print(f"Metadata file not found: {metadata_path}")
            # Create basic metadata
            metadata = {
                "title": f"Video {datetime.now().strftime('%Y-%m-%d')}",
                "content": "Automatically generated video",
                "keywords": ["educational", "shorts", "facts"]
            }
            
            # Save it for future reference
            try:
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=4)
                print(f"Created basic metadata file")
            except Exception as e:
                print(f"Error creating metadata file: {str(e)}")
            
        # Upload to YouTube
        if os.path.exists(video_path):
            print(f"Last generated video: {video_path}")
            print(f"Title: {metadata.get('title', 'Untitled Video')}")
            
            # Ask user
            response = input("Do you want to upload this video to YouTube? (y/n): ")
            
            if response.lower() in ["y", "yes"]:
                result = uploader.upload_video(
                    video_path=video_path,
                    title=metadata.get("title", "Automatically Generated Video"),
                    description=metadata.get("content", ""),
                    tags=metadata.get("keywords", []) + ["Shorts", "shortvideo"],
                    category=metadata.get("category_id", "27"),  # Default to Education
                    is_shorts=True
                )
                
                if result and result.get("success", False):
                    if result.get("video_id"):
                        print(f"Video successfully uploaded: {result.get('video_url', '')}")
                        if result.get('shorts_url'):
                            print(f"Shorts URL: {result.get('shorts_url', '')}")
                            
                        # Update metadata with YouTube info
                        metadata["youtube_url"] = result.get("video_url", "")
                        metadata["youtube_shorts_url"] = result.get("shorts_url", "")
                        metadata["youtube_video_id"] = result.get("video_id", "")
                        
                        # Save updated metadata
                        try:
                            with open(metadata_path, "w", encoding="utf-8") as f:
                                json.dump(metadata, f, ensure_ascii=False, indent=4)
                            print("Updated metadata with YouTube information")
                        except Exception as e:
                            print(f"Error updating metadata file: {str(e)}")
                    else:
                        print(f"Info: {result.get('message', 'Video upload successful but ID not retrieved')}")
                else:
                    error_msg = result.get('error', 'Unknown error') if result else "Upload result not received"
                    print(f"Video upload error: {error_msg}")
        else:
            print(f"Metadata file not found: {metadata_path}")
    else:
        print("No videos found.") 