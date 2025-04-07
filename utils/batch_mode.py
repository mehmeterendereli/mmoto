#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
from typing import List
import random

def process_batch(topic_list: List[str], max_videos: int = 10, delay_minutes: int = 5) -> None:
    """
    Birden fazla konu için toplu video üretir
    
    Args:
        topic_list (List[str]): İşlenecek konuların listesi
        max_videos (int): Üretilecek maksimum video sayısı
        delay_minutes (int): Her video arasında beklenecek süre (dakika)
    """
    if not topic_list:
        print("Uyarı: İşlenecek konu listesi boş!")
        return
    
    # Konfigürasyon dosyasını kontrol et
    if not os.path.exists('config.json'):
        print("Hata: config.json dosyası bulunamadı!")
        return
    
    # Ana modülleri import et
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
    
    # Konfigürasyon dosyasını yükle
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # İşlenecek video sayısını belirle
    process_count = min(len(topic_list), max_videos)
    
    # Konuları karıştır
    random.shuffle(topic_list)
    
    # Belirlenen sayıda videoyu işle
    for i in range(process_count):
        try:
            topic = topic_list[i]
            print(f"\n{'-' * 50}")
            print(f"Video {i+1}/{process_count} işleniyor: '{topic}'")
            print(f"{'-' * 50}\n")
            
            # Yeni proje klasörünü oluştur
            project_folder = create_project_folder()
            print(f"Proje klasörü oluşturuldu: {project_folder}")
            
            # İçerik üret
            content_data = generate_content(topic)
            print("İçerik üretildi")
            
            # Anahtar kelimeleri çıkar
            keywords = extract_keywords(content_data["response"])
            print(f"Anahtar kelimeler: {keywords}")
            
            # Videoları getir
            videos = fetch_videos(keywords, config["pexels_api_key"], project_folder)
            print(f"{len(videos)} adet video indirildi")
            
            # Videoları işle
            processed_video = process_videos(videos, config["video_resolution"], project_folder)
            print("Videolar işlendi")
            
            # TTS oluştur
            audio_files = generate_tts(content_data["response"], config["openai_api_key"], 
                                      config["default_tts_voice"], project_folder)
            print(f"{len(audio_files)} adet ses dosyası oluşturuldu")
            
            # Sesleri videoyla birleştir
            video_with_audio = merge_audio(processed_video, audio_files, project_folder)
            print("Sesler birleştirildi")
            
            # Altyazıları ekle (eğer etkinleştirilmişse)
            use_subtitles = config.get("use_subtitles", False)
            if use_subtitles:
                print(f"Altyazılar ekleniyor")
                subtitled_video = render_subtitles(video_with_audio, content_data["response"], 
                                                  config["font_path"], project_folder)
                print("Altyazılar eklendi")
            else:
                print("Altyazı gösterme devre dışı, işlem atlanıyor")
                subtitled_video = video_with_audio
            
            # Kapanış sahnesini ekle
            final_video = add_closing_scene(subtitled_video, config["closing_video_path"], project_folder)
            print("Kapanış sahnesi eklendi")
            
            # Metadata oluştur
            write_metadata(project_folder, topic, keywords, "gpt-4o", config["default_tts_voice"])
            print("Metadata oluşturuldu")
            
            print(f"Video tamamlandı: {final_video}")
            
            # Son video değilse bekle
            if i < process_count - 1:
                print(f"{delay_minutes} dakika bekleniyor...")
                time.sleep(delay_minutes * 60)
                
        except Exception as e:
            print(f"Toplu işleme hatası ('{topic}'): {str(e)}")
    
    print(f"\nToplu işleme tamamlandı. {process_count} video oluşturuldu.") 