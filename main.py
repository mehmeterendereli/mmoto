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
        
        # YouTube'a video yükleme
        upload_choice = input("Video YouTube'a yüklensin mi? (e/h): ")
        if upload_choice.lower() in ["e", "evet", "y", "yes"]:
            try:
                # Başlık ve açıklama hazırla (YouTube karakter limitleri: başlık 100, açıklama 5000)
                title = metadata.get("title", "Otomatik Oluşturulmuş Video")
                if len(title) > 100:
                    title = title[:97] + "..."
                    
                description = metadata.get("content", "")
                if len(description) > 5000:
                    description = description[:4997] + "..."
                
                # Video etiketleri hazırla
                tags = metadata.get("keywords", []) + ["Shorts", "kısavideo"]
                
                # YouTube uploader'ı başlat
                uploader = YouTubeUploader()
                
                result = uploader.upload_video(
                    video_path=final_video,
                    title=title,
                    description=description,
                    tags=tags,
                    category="22",  # İnsanlar ve Bloglar
                    privacy_status="public",  # public, private veya unlisted
                    is_shorts=True  # YouTube Shorts olarak yükle
                )
                
                if result and result.get("success", False):
                    if result.get("video_id"):
                        logger.info(f"Video başarıyla YouTube'a yüklendi: {result.get('video_url', '')}")
                        print(f"Video YouTube'a yüklendi: {result.get('video_url', '')}")
                        
                        if result.get('shorts_url'):
                            print(f"Shorts URL: {result.get('shorts_url', '')}")
                        
                        # Metadata'ya YouTube bilgilerini de ekle
                        metadata["youtube_url"] = result.get("video_url", "")
                        metadata["youtube_shorts_url"] = result.get("shorts_url", "")
                        metadata["youtube_video_id"] = result.get("video_id", "")
                        
                        # Güncellenmiş metadata'yı kaydet
                        metadata_path = os.path.join(project_folder, "metadata.json")
                        with open(metadata_path, "w", encoding="utf-8") as f:
                            json.dump(metadata, f, ensure_ascii=False, indent=2)
                    else:
                        # Video ID yoksa, manuel yükleme mesajını göster
                        logger.info(f"Video kopyalandı ama ID alınmadı: {result.get('message', '')}")
                        print(f"Bilgi: {result.get('message', 'Video yükleme tamamlandı fakat ID alınamadı')}")
                else:
                    error_msg = result.get('error', 'Bilinmeyen hata') if result else "Yükleme sonucu alınamadı"
                    logger.error(f"YouTube yükleme hatası: {error_msg}")
                    print(f"YouTube yükleme hatası: {error_msg}")
                    
            except Exception as e:
                error_msg = f"YouTube yükleme işlemi sırasında hata: {str(e)}"
                logger.error(error_msg)
                print(error_msg)
        
    except Exception as e:
        logger.error(f"Hata oluştu: {str(e)}", exc_info=True)

def main():
    """Normal şekilde çağrılan ana fonksiyon, asenkron işlemleri yönetir"""
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
