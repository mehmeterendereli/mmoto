#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import datetime

def write_metadata(project_folder: str, topic: str, keywords: list, model_name: str, voice_name: str) -> None:
    """
    Video için metadata oluşturur
    
    Args:
        project_folder (str): Proje klasörünün yolu
        topic (str): Video konusu
        keywords (list): Anahtar kelimeler
        model_name (str): Kullanılan yapay zeka modeli
        voice_name (str): Kullanılan ses
    """
    try:
        # Metadata dosyasının yolu
        metadata_path = os.path.join(project_folder, "metadata.json")
        
        # Metadata bilgileri
        metadata = {
            "topic": topic,
            "keywords": keywords,
            "creation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": model_name,
            "voice": voice_name,
            "project_folder": project_folder
        }
        
        # Metadata dosyasını oluştur
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
        
        print(f"Metadata dosyası oluşturuldu: {metadata_path}")
        
        # İstatistikler dosyası için klasör varlığını kontrol et
        stats_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stats")
        os.makedirs(stats_folder, exist_ok=True)
        
        # Tüm videoların listesini tutan bir dosya oluştur
        videos_list_path = os.path.join(stats_folder, "videos.json")
        
        # Mevcut video listesini yükle veya yeni oluştur
        videos_list = []
        if os.path.exists(videos_list_path):
            try:
                with open(videos_list_path, "r", encoding="utf-8") as f:
                    videos_list = json.load(f)
            except:
                videos_list = []
        
        # Yeni video bilgilerini ekle
        video_info = {
            "topic": topic,
            "project_folder": os.path.basename(project_folder),
            "creation_date": metadata["creation_date"],
            "keywords": keywords
        }
        videos_list.append(video_info)
        
        # Dosyaya kaydet
        with open(videos_list_path, "w", encoding="utf-8") as f:
            json.dump(videos_list, f, ensure_ascii=False, indent=4)
            
        print(f"Video istatistik listesi güncellendi: {videos_list_path}")
        
    except Exception as e:
        print(f"Metadata oluşturma hatası: {str(e)}")
        # Yine de temel bir metadata dosyası oluşturmaya çalış
        try:
            basic_metadata = {
                "topic": topic,
                "creation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(os.path.join(project_folder, "basic_metadata.json"), "w", encoding="utf-8") as f:
                json.dump(basic_metadata, f, ensure_ascii=False, indent=4)
        except:
            pass 