#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import logging
from datetime import datetime

# Modülleri import et
from modules.project_initializer import create_project_folder
from modules.content_generator import generate_content
from modules.keyword_extractor import extract_keywords
from modules.video_fetcher import fetch_videos
from modules.video_processor import process_videos
from modules.tts_generator import generate_tts
from modules.subtitle_renderer import render_subtitles
from modules.audio_merger import merge_audio
from modules.closing_scene_adder import add_closing_scene
from modules.metadata_writer import write_metadata

def load_config():
    """Konfigürasyon dosyasını yükler"""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    # Loglama ayarları
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('merak_makinesi')
    
    try:
        # Konfigürasyon dosyasını yükle
        config = load_config()
        
        # Kullanıcıdan konu al
        topic = input("Lütfen bir konu girin: ")
        
        # Yeni proje klasörünü oluştur
        project_folder = create_project_folder()
        logger.info(f"Proje klasörü oluşturuldu: {project_folder}")
        
        # İçerik üret
        content_data = generate_content(topic)
        logger.info("İçerik üretildi")
        
        # Anahtar kelimeleri çıkar
        keywords = extract_keywords(content_data["response"], topic)
        logger.info(f"Anahtar kelimeler: {keywords}")
        
        # Videoları getir
        videos = fetch_videos(keywords, config["pexels_api_key"], project_folder)
        logger.info(f"{len(videos)} adet video indirildi")
        
        # Videoları işle
        processed_video = process_videos(videos, config["video_resolution"], project_folder)
        logger.info("Videolar işlendi")
        
        # TTS oluştur
        audio_files = generate_tts(content_data["response"], config["openai_api_key"], 
                                  config["default_tts_voice"], project_folder)
        logger.info(f"{len(audio_files)} adet ses dosyası oluşturuldu")
        
        # Altyazıları ekle
        subtitled_video = render_subtitles(processed_video, content_data["response"], 
                                          config["font_path"], project_folder)
        logger.info("Altyazılar eklendi")
        
        # Sesleri birleştir
        video_with_audio = merge_audio(subtitled_video, audio_files, project_folder)
        logger.info("Sesler birleştirildi")
        
        # Kapanış sahnesini ekle
        final_video = add_closing_scene(video_with_audio, config["closing_video_path"], project_folder)
        logger.info("Kapanış sahnesi eklendi")
        
        # Metadata oluştur
        write_metadata(project_folder, topic, keywords, "gpt-4o", config["default_tts_voice"])
        logger.info("Metadata oluşturuldu")
        
        logger.info(f"İşlem tamamlandı! Final video: {final_video}")
        
    except Exception as e:
        logger.error(f"Hata oluştu: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
