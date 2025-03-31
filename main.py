#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import logging
from datetime import datetime

# Temel modülleri import et
from modules.project_initializer import create_project_folder
from modules.tts_generator import generate_tts
from modules.subtitle_renderer import render_subtitles
from modules.audio_merger import merge_audio
from modules.closing_scene_adder import add_closing_scene
from modules.metadata_writer import write_metadata

# Yeni akıllı modülleri import et
from modules.smart_content_planner import generate_structured_content, create_visual_storyboard
from modules.smart_media_fetcher import extract_media_requirements, fetch_smart_media, select_optimal_media
from modules.smart_video_processor import process_media_based_on_storyboard, generate_production_instructions

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
        
        # ====== YENİ AKILLI İÇERİK PLANLAMA SÜRECİ ======
        # Yapılandırılmış içeriği üret
        structured_content = generate_structured_content(topic)
        logger.info("Yapılandırılmış içerik üretildi")
        
        # Görsel hikaye akışı oluştur
        storyboard = create_visual_storyboard(structured_content)
        logger.info("Görsel hikaye akışı oluşturuldu")
        
        # Medya gereksinimlerini çıkar
        media_requirements = extract_media_requirements(structured_content)
        logger.info(f"{len(media_requirements)} adet medya gereksinimi çıkarıldı")
        
        # ====== YENİ AKILLI MEDYA ARAMA VE İNDİRME ======
        logger.info("GPT-4o ile thumbnail analizi kullanılarak medya araması başlatılıyor...")
        # Akıllı medya indirme (OpenAI API anahtarı geçiyoruz)
        media_files = fetch_smart_media(media_requirements, config["pexels_api_key"], 
                                       project_folder, config.get("openai_api_key", ""))
        video_count = len(media_files.get("videos", []))
        photo_count = len(media_files.get("photos", []))
        logger.info(f"GPT-4o thumbnail analizi ile {video_count} video ve {photo_count} fotoğraf indirildi")
        
        # Medyaları storyboarda göre eşleştir
        media_mapping = select_optimal_media(storyboard, media_files, config.get("openai_api_key", ""))
        logger.info("Medya eşleme tamamlandı")
        
        # Üretim talimatları oluştur
        production_instructions = generate_production_instructions(media_mapping, config.get("openai_api_key", ""))
        logger.info("Üretim talimatları oluşturuldu")
        
        # Medyaları işle
        processed_video = process_media_based_on_storyboard(media_mapping, project_folder, config["video_resolution"])
        logger.info("Medyalar işlendi")
        
        # ====== SES VE ALTYAZI ======
        # TTS oluştur - artık yapılandırılmış içerikten alıyoruz
        all_content_text = []
        
        # Giriş
        if "introduction" in structured_content:
            all_content_text.append(structured_content["introduction"])
        
        # Ana içerik
        if "main_content" in structured_content:
            for content in structured_content["main_content"]:
                all_content_text.append(content["text"])
        
        # Sonuç
        if "conclusion" in structured_content:
            all_content_text.append(structured_content["conclusion"])
        
        audio_files = generate_tts(all_content_text, config["openai_api_key"], 
                                  config["default_tts_voice"], project_folder)
        logger.info(f"{len(audio_files)} adet ses dosyası oluşturuldu")
        
        # Altyazıları ekle
        subtitled_video = render_subtitles(processed_video, all_content_text, 
                                          config["font_path"], project_folder)
        logger.info("Altyazılar eklendi")
        
        # Sesleri birleştir
        video_with_audio = merge_audio(subtitled_video, audio_files, project_folder)
        logger.info("Sesler birleştirildi")
        
        # Kapanış sahnesini ekle
        final_video = add_closing_scene(video_with_audio, config["closing_video_path"], project_folder)
        logger.info("Kapanış sahnesi eklendi")
        
        # Metadata oluştur
        write_metadata(project_folder, topic, structured_content.get("visual_keywords", ["education"]), 
                    "gpt-4o", config["default_tts_voice"])
        logger.info("Metadata oluşturuldu")
        
        logger.info(f"İşlem tamamlandı! Final video: {final_video}")
        
    except Exception as e:
        logger.error(f"Hata oluştu: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
