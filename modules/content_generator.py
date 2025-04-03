#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import openai
from openai import OpenAI
import re
from typing import Dict, Any

def generate_content(topic: str) -> Dict[str, Any]:
    """
    Generates informative text content for a given topic
    
    Args:
        topic (str): Content topic
    
    Returns:
        Dict[str, Any]: Generated content information
    """
    # Get OpenAI API key from configuration file
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    api_key = ""
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                api_key = config.get("openai_api_key", "")
        except:
            pass
    
    if not api_key:
        print("Warning: OpenAI API key not found!")
        # Return dummy content
        return {
            "topic": topic,
            "response": [
                "This is a sample content.",
                f"No information found about {topic}.",
                "Please check your API key."
            ]
        }
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Generate content using GPT-4o
        prompt = f"""
        Write a short, informative text about {topic}.
        This text will be narrated by TTS for a video.
        
        Important Rules:
        1. The text should get straight to the point, no unnecessary introductions like "hello, today I'll talk about..."
        2. Each sentence should be a separate paragraph, no lists or numbered items
        3. Total of 7 sentences and the entire text should take approximately 45 seconds when narrated (NEVER exceed 50 seconds)
        4. Each sentence should be meaningful and educational
        5. Target audience is general viewers, so use non-technical language
        6. Each sentence should be between 12-20 words in length and in English
        7. The text should consist of only plain sentences, just 7 sentences in total
        8. Each sentence should include a 2-4 second breathing pause (for naturalness)
        
        Please create a text that fully complies with the above rules, with a total of 7 sentences that will take 35-45 seconds when read by TTS.
        Provide each sentence as a separate paragraph.
        """
        
        # Send request
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that creates short, informative content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Get and process the response
        content = response.choices[0].message.content
        
        # Split the response into sentences - each paragraph is a sentence
        sentences = []
        for paragraph in content.strip().split('\n'):
            paragraph = paragraph.strip()
            if paragraph:  # Skip empty paragraphs
                # Remove bullet points and numbers if present
                cleaned = re.sub(r'^\d+\.\s*|\*\s*|\-\s*', '', paragraph)
                sentences.append(cleaned)
        
        # Check sentence count and adjust if needed
        if len(sentences) > 7:
            sentences = sentences[:7]  # Maximum 7 sentences
        
        # Return results
        return {
            "topic": topic,
            "response": sentences
        }
    
    except Exception as e:
        print(f"Content generation error: {str(e)}")
        # Return dummy content in case of error
        return {
            "topic": topic,
            "response": [
                f"An error occurred while creating content about {topic}.",
                "There was a problem communicating with the API.",
                "Please try again later."
            ]
        } 