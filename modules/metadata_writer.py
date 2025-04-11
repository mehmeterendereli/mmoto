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
                "title": f"İlginç {topic.title()} GERÇEKLER",
                "description": "\n\n".join(content) + "\n\n#Shorts #Educational #Knowledge",
                "tags": ["educational", "shorts", "facts", "knowledge"] + topic.lower().split()
            }
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Full text content
        full_content = " ".join(content)
        
        # Generate optimized metadata with OpenAI
        prompt = f"""
        Sen bir viral YouTube Shorts ve TikTok içerik uzmanısın. "{topic}" konulu bir video için aşırı clickbait ve izlenmesi yüksek metadata üretmen gerekiyor.
        
        Video içeriği:
        {full_content}
        
        Aşağıdakileri oluştur:
        1. Merak uyandıran ve HEMEN tıklanacak bir başlık (max 60 karakter). Başlık ilgi çekici olmalı. İzleyicilerin geçip gitmesini ASLA istemiyoruz!
        2. İzleyiciyi hemen yakalayacak açıklama. Her cümle başlığı desteklemeli ve merak uyandırmalı. Sonda mutlaka uygun hashtag'ler olmalı.
        3. Viral olacak 8-10 ilgili etiket (tek kelimeler veya kısa ifadeler, hashtagsiz)
        4. En uygun YouTube kategori kimliğini şu listeden seç:
           - 1: Film & Animasyon
           - 2: Otomobil & Taşıtlar
           - 10: Müzik
           - 15: Evcil Hayvanlar & Hayvanlar
           - 17: Spor
           - 18: Kısa Filmler
           - 19: Seyahat & Olaylar
           - 20: Oyun
           - 22: Kişiler & Bloglar
           - 23: Komedi
           - 24: Eğlence
           - 25: Haberler & Politika
           - 26: Nasıl Yapılır & Stil
           - 27: Eğitim
           - 28: Bilim & Teknoloji
           - 29: Kâr Amacı Gütmeyen & Aktivizm
        
        Yanıtını şu JSON formatında ver: {{"title": "...", "description": "...", "tags": [...], "category_id": "..."}}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Sen viral YouTube Shorts ve TikTok kanalları için içerik stratejisti olarak çalışıyorsun. İzlenme oranlarını patlatacak içerikler üretmekte ustasın."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.8
        )
        
        # Parse JSON response
        metadata = json.loads(response.choices[0].message.content)
        
        # Ensure values exist and are properly formatted
        if "title" not in metadata or not metadata["title"]:
            metadata["title"] = f"işte {topic.title()} GERÇEKLER!"
            
        if "description" not in metadata or not metadata["description"]:
            metadata["description"] = "\n\n".join(content) + "\n\n#Shorts #Educational #Knowledge #Viral #MustWatch"
            
        if "tags" not in metadata or not metadata["tags"] or not isinstance(metadata["tags"], list):
            metadata["tags"] = ["viral", "educational", "shorts", "facts", "mustwatch", "trending"] + topic.lower().split()
        
        if "category_id" not in metadata or not metadata["category_id"]:
            metadata["category_id"] = "27"  # Default to Education
            
        return metadata
        
    except Exception as e:
        print(f"Error generating YouTube metadata: {str(e)}")
        # Fallback metadata
        return {
            "title": f"Bak  {topic.title()}",
            "description": "\n\n".join(content) + "\n\n#Shorts #Viral #MustWatch #Educational",
            "tags": ["viral", "shorts", "facts", "mustwatch", "trending"] + topic.lower().split(),
            "category_id": "27"  # Education
        }

def write_metadata(project_folder: str, topic: str, keywords: list, model_name: str, voice_name: str, 
                language: str = "tr", tts_language: str = "tr", subtitle_language: str = "tr") -> Dict[str, Any]:
    """
    Creates metadata for the video
    
    Args:
        project_folder (str): Path to the project folder
        topic (str): Video topic
        keywords (list): Keywords
        model_name (str): AI model used
        voice_name (str): Voice used
        language (str): Content language
        tts_language (str): TTS language
        subtitle_language (str): Subtitle language
    
    Returns:
        Dict[str, Any]: Created metadata
    """
    try:
        # Metadata file path
        metadata_path = os.path.join(project_folder, "metadata.json")
        
        # Get OpenAI API key
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        api_key = ""
        
        # Varsayılan ses modeli için config'i kontrol et
        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    api_key = config.get("openai_api_key", "")
                    
                    # Eğer voice_name parametresi varsayılan "alloy" ise ve config'de başka bir değer varsa
                    if voice_name == "alloy" and "default_tts_voice" in config:
                        voice_name = config.get("default_tts_voice")
                        print(f"Voice model updated from 'alloy' to '{voice_name}' from config")
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
            "project_folder": project_folder,
            "language": language,
            "tts_language": tts_language,
            "subtitle_language": subtitle_language
        }
        
        # Create metadata file
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
        
        print(f"Metadata file created: {metadata_path}")
        print(f"Using TTS voice model: {voice_name}")
        
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
            "keywords": keywords,
            "language": language,
            "tts_language": tts_language,
            "subtitle_language": subtitle_language
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
                "creation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "language": language,
                "tts_language": tts_language,
                "subtitle_language": subtitle_language
            }
            with open(os.path.join(project_folder, "basic_metadata.json"), "w", encoding="utf-8") as f:
                json.dump(basic_metadata, f, ensure_ascii=False, indent=4)
            return basic_metadata
        except:
            return {
                "topic": topic,
                "title": f"Facts About {topic}",
                "keywords": keywords,
                "language": language,
                "tts_language": tts_language,
                "subtitle_language": subtitle_language
            } 