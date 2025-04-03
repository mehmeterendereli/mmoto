#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import datetime
import re
from typing import Dict, Any, List
import openai
from openai import OpenAI

def generate_youtube_metadata(topic: str, content: List[str], api_key: str) -> Dict[str, Any]:
    """
    Generates optimized metadata for YouTube using AI
    
    Args:
        topic (str): Video topic
        content (List[str]): List of sentences in the video
        api_key (str): OpenAI API key
        
    Returns:
        Dict[str, Any]: YouTube optimized metadata
    """
    try:
        # Generate YouTube metadata using OpenAI
        if not api_key:
            # Fallback if no API key
            return {
                "title": f"Interesting Facts About {topic.title()}",
                "description": "\n\n".join(content) + "\n\n#Shorts #Educational #Knowledge",
                "tags": ["educational", "shorts", "facts", "knowledge"] + topic.lower().split()
            }
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Full text content
        full_content = " ".join(content)
        
        # Generate optimized metadata with OpenAI
        prompt = f"""
        Create YouTube Shorts metadata for a video about "{topic}". The video content is:
        
        {full_content}
        
        Generate the following:
        1. A catchy title (max 60 chars) that includes the topic and will get clicks
        2. An engaging description that summarizes the content and includes hashtags
        3. 8-10 relevant tags (single words or short phrases, no hashtags in tags)
        4. The most appropriate YouTube category ID number from this list:
           - 1: Film & Animation
           - 2: Autos & Vehicles
           - 10: Music
           - 15: Pets & Animals
           - 17: Sports
           - 18: Short Movies
           - 19: Travel & Events
           - 20: Gaming
           - 22: People & Blogs
           - 23: Comedy
           - 24: Entertainment
           - 25: News & Politics
           - 26: Howto & Style
           - 27: Education
           - 28: Science & Technology
           - 29: Nonprofit & Activism
        
        Format as JSON with keys: "title", "description", "tags" (as array), "category_id" (as string)
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a YouTube metadata specialist who creates engaging titles and descriptions."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        # Parse JSON response
        metadata = json.loads(response.choices[0].message.content)
        
        # Ensure values exist and are properly formatted
        if "title" not in metadata or not metadata["title"]:
            metadata["title"] = f"Amazing Facts About {topic.title()} | Shorts"
            
        if "description" not in metadata or not metadata["description"]:
            metadata["description"] = "\n\n".join(content) + "\n\n#Shorts #Educational #Knowledge"
            
        if "tags" not in metadata or not metadata["tags"] or not isinstance(metadata["tags"], list):
            metadata["tags"] = ["educational", "shorts", "facts", "knowledge"] + topic.lower().split()
        
        if "category_id" not in metadata or not metadata["category_id"]:
            metadata["category_id"] = "27"  # Default to Education
            
        return metadata
        
    except Exception as e:
        print(f"Error generating YouTube metadata: {str(e)}")
        # Fallback metadata
        return {
            "title": f"Interesting Facts About {topic.title()}",
            "description": "\n\n".join(content) + "\n\n#Shorts #Educational #Knowledge",
            "tags": ["educational", "shorts", "facts", "knowledge"] + topic.lower().split(),
            "category_id": "27"  # Education
        }

def write_metadata(project_folder: str, topic: str, keywords: list, model_name: str, voice_name: str) -> Dict[str, Any]:
    """
    Creates metadata for the video
    
    Args:
        project_folder (str): Path to the project folder
        topic (str): Video topic
        keywords (list): Keywords
        model_name (str): AI model used
        voice_name (str): Voice used
    
    Returns:
        Dict[str, Any]: Created metadata
    """
    try:
        # Metadata file path
        metadata_path = os.path.join(project_folder, "metadata.json")
        
        # Get OpenAI API key
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        api_key = ""
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    api_key = config.get("openai_api_key", "")
            except:
                pass
        
        # Get content from text files if available
        content_sentences = []
        text_files = [f for f in os.listdir(project_folder) if f.startswith("text_") and f.endswith(".txt")]
        if text_files:
            for text_file in sorted(text_files):
                try:
                    with open(os.path.join(project_folder, text_file), "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            content_sentences.append(content)
                except:
                    pass
        
        # Generate YouTube-optimized metadata
        youtube_metadata = generate_youtube_metadata(topic, content_sentences, api_key)
        
        # Metadata information
        metadata = {
            "topic": topic,
            "title": youtube_metadata["title"],
            "content": youtube_metadata["description"],
            "keywords": keywords + youtube_metadata["tags"],
            "category_id": youtube_metadata["category_id"],
            "creation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": model_name,
            "voice": voice_name,
            "project_folder": project_folder
        }
        
        # Create metadata file
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
        
        print(f"Metadata file created: {metadata_path}")
        
        # Check if stats folder exists
        stats_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stats")
        os.makedirs(stats_folder, exist_ok=True)
        
        # Create a file that holds the list of all videos
        videos_list_path = os.path.join(stats_folder, "videos.json")
        
        # Load existing video list or create new
        videos_list = []
        if os.path.exists(videos_list_path):
            try:
                with open(videos_list_path, "r", encoding="utf-8") as f:
                    videos_list = json.load(f)
            except:
                videos_list = []
        
        # Add new video information
        video_info = {
            "topic": topic,
            "title": metadata["title"],
            "project_folder": os.path.basename(project_folder),
            "creation_date": metadata["creation_date"],
            "keywords": keywords
        }
        videos_list.append(video_info)
        
        # Save to file
        with open(videos_list_path, "w", encoding="utf-8") as f:
            json.dump(videos_list, f, ensure_ascii=False, indent=4)
            
        print(f"Video statistics list updated: {videos_list_path}")
        
        return metadata
        
    except Exception as e:
        print(f"Metadata creation error: {str(e)}")
        # Still try to create a basic metadata file
        try:
            basic_metadata = {
                "topic": topic,
                "title": f"Facts About {topic.title()}",
                "content": f"Interesting information about {topic}.",
                "keywords": keywords,
                "category_id": "27",  # Education
                "creation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(os.path.join(project_folder, "basic_metadata.json"), "w", encoding="utf-8") as f:
                json.dump(basic_metadata, f, ensure_ascii=False, indent=4)
            return basic_metadata
        except:
            return {
                "topic": topic,
                "title": f"Facts About {topic}",
                "keywords": keywords
            } 