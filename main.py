#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import logging
import asyncio
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
from modules.youtube_uploader import YouTubeUploader

def load_config():
    """Konfigürasyon dosyasını yükler"""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

async def async_main():
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
        
        # Yeni asenkron video getirme fonksiyonunu kullan
        videos = await fetch_videos(
            keywords, 
            config["pexels_api_key"], 
            config["openai_api_key"], 
            topic, 
            content_data["response"], 
            project_folder, 
            min_score=5.0  # 7.0'dan 5.0'a düşürüldü
        )
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
        metadata = write_metadata(project_folder, topic, keywords, "gpt-4o", config["default_tts_voice"])
        logger.info("Metadata oluşturuldu")
        
        logger.info(f"İşlem tamamlandı! Final video: {final_video}")
        
        # Kullanıcıya YouTube'a yükleme seçeneği sun
        upload_choice = input("Video YouTube'a yüklensin mi? (e/h): ")
        
        if upload_choice.lower() in ['e', 'evet', 'y', 'yes']:
            try:
                # YouTube yükleyiciyi başlat
                uploader = YouTubeUploader(
                    client_secrets_file=os.path.join(os.path.dirname(__file__), "client_secret.json"),
                    credentials_file=os.path.join(os.path.dirname(__file__), "youtube_token.json")
                )
                
                # Video başlığını hazırla
                video_title = metadata.get("title", topic)
                if len(video_title) > 100:  # YouTube başlık limiti
                    video_title = video_title[:97] + "..."
                
                # Video açıklamasını hazırla
                video_description = metadata.get("content", "")
                if len(video_description) > 5000:  # YouTube açıklama limiti
                    video_description = video_description[:4997] + "..."
                
                # Etiketleri hazırla
                video_tags = metadata.get("keywords", [])
                # Shorts etiketlerini ekle
                video_tags.extend(["Shorts", "kısavideo", "bilgi"])
                
                # Kategori seç (varsayılan: eğitim)
                video_category = "education"
                
                logger.info("Video YouTube'a yükleniyor...")
                
                # Videoyu yükle
                result = uploader.upload_video(
                    video_path=final_video,
                    title=video_title,
                    description=video_description,
                    tags=video_tags,
                    category=video_category,
                    privacy_status="public",  # veya "unlisted", "private"
                    is_shorts=True
                )
                
                if result["success"]:
                    logger.info(f"Video başarıyla YouTube'a yüklendi: {result['video_url']}")
                    logger.info(f"Shorts URL: {result['shorts_url']}")
                    print(f"Video YouTube'a yüklendi: {result['video_url']}")
                    print(f"Shorts URL: {result['shorts_url']}")
                else:
                    logger.error(f"YouTube yükleme hatası: {result['error']}")
                    print(f"YouTube yükleme hatası: {result['error']}")
            
            except Exception as e:
                logger.error(f"YouTube yükleme işlemi sırasında hata: {str(e)}")
                print(f"YouTube yükleme hatası: {str(e)}")
        
    except Exception as e:
        logger.error(f"Hata oluştu: {str(e)}", exc_info=True)

def main():
    """Normal şekilde çağrılan ana fonksiyon, asenkron işlemleri yönetir"""
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
