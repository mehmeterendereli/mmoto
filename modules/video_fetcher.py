#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import requests
import time
import shutil
from typing import List, Dict

def fetch_videos(keywords: List[str], api_key: str, project_folder: str) -> List[str]:
    """
    Pexels API kullanarak anahtar kelimelere göre video arar ve indirir
    
    Args:
        keywords (List[str]): Aranacak anahtar kelimeler
        api_key (str): Pexels API anahtarı
        project_folder (str): Proje klasörünün yolu
    
    Returns:
        List[str]: İndirilen video dosyalarının yolları
    """
    if not api_key:
        print("Uyarı: Pexels API anahtarı boş. Daha önce indirilmiş videoları kullan.")
        return []
    
    downloaded_videos = []
    video_folder = os.path.join(project_folder, "pexels_videos")
    
    # Her anahtar kelime için arama yap
    for keyword in keywords:
        try:
            # Pexels API'ye istek gönder
            headers = {
                "Authorization": api_key
            }
            
            # Dikey ve yatay videoları karışık olarak al
            url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=5"
            
            print(f"'{keyword}' için Pexels API'ye istek gönderiliyor...")
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if "videos" in data and len(data["videos"]) > 0:
                    print(f"{len(data['videos'])} adet video bulundu")
                    
                    # Her video için
                    for i, video in enumerate(data["videos"]):
                        try:
                            # En yüksek çözünürlüklü video dosyasını bul
                            video_files = video.get("video_files", [])
                            portrait_videos = [v for v in video_files if v.get("width", 0) < v.get("height", 0)]
                            
                            if not portrait_videos:
                                portrait_videos = video_files
                            
                            # Çözünürlüğe göre sırala (en yüksek başta)
                            if portrait_videos:
                                portrait_videos.sort(key=lambda x: x.get("width", 0) * x.get("height", 0), reverse=True)
                                video_url = portrait_videos[0].get("link")
                                
                                if video_url:
                                    # Dosya adını belirle
                                    video_path = os.path.join(video_folder, f"video_{keyword}_{i+1}.mp4")
                                    
                                    # İndir
                                    print(f"Video indiriliyor: {video_url[:50]}...")
                                    
                                    try:
                                        # Daha güvenli indirme yöntemi
                                        local_filename = download_file(video_url, video_path)
                                        if local_filename:
                                            downloaded_videos.append(local_filename)
                                            print(f"Video başarıyla indirildi: {local_filename}")
                                    except Exception as e:
                                        print(f"Video indirme hatası: {str(e)}")
                                        
                                    # API limitlerini aşmamak için biraz bekle
                                    time.sleep(1)
                        except Exception as inner_e:
                            print(f"Video işleme hatası: {str(inner_e)}")
                            continue
                else:
                    print(f"'{keyword}' için sonuç bulunamadı!")
            else:
                print(f"API hatası: {response.status_code} - {response.text}")
            
            # Her anahtar kelime araması arasında biraz bekle
            time.sleep(2)
            
        except Exception as e:
            print(f"Video arama hatası ({keyword}): {str(e)}")
            time.sleep(3)  # Hata durumunda daha uzun bekle
    
    # En az bir video indirildi mi kontrol et
    if not downloaded_videos:
        print("Hiç video indirilemedi, varsayılan video kullanılacak...")
        # Buraya varsayılan video ekleme kodu gelebilir
    
    return downloaded_videos

def download_file(url: str, destination: str) -> str:
    """
    Belirtilen URL'den dosyayı güvenli bir şekilde indirir
    
    Args:
        url (str): İndirilecek dosyanın URL'si
        destination (str): Kaydedilecek dosyanın yolu
    
    Returns:
        str: İndirilen dosyanın yolu veya hata durumunda boş string
    """
    try:
        # İndirme işlemi için geçici dosya kullan
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            
            # Geçici dosyaya kaydet
            temp_file = destination + ".temp"
            with open(temp_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Geçici dosyayı hedef dosyaya taşı
            shutil.move(temp_file, destination)
            
            return destination
    except Exception as e:
        print(f"Dosya indirme hatası: {str(e)}")
        # Geçici dosyayı temizle
        if os.path.exists(destination + ".temp"):
            os.remove(destination + ".temp")
        return ""
