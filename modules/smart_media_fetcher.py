#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import requests
import time
import shutil
import logging
from typing import List, Dict, Any, Tuple

from modules.thumbnail_analyzer import batch_analyze_thumbnails

logger = logging.getLogger('merak_makinesi')

def extract_media_requirements(structured_content: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Yapılandırılmış içerikten medya gereksinimlerini çıkarır
    
    Args:
        structured_content (Dict[str, Any]): Yapılandırılmış içerik
    
    Returns:
        List[Dict[str, Any]]: Medya gereksinimleri
    """
    media_requirements = []
    
    # Giriş cümlesi için gereksinim
    if "introduction" in structured_content:
        media_requirements.append({
            "text": structured_content["introduction"],
            "media_type": "video",  # Giriş için video tercih ediyoruz
            "keywords": ["introduction", "opening", structured_content.get("topic", "education")],
            "scene_id": 0
        })
    
    # Ana içerik için gereksinimler
    if "main_content" in structured_content:
        for i, content in enumerate(structured_content["main_content"]):
            media_requirements.append({
                "text": content["text"],
                "media_type": content.get("media_type", "video"),
                "keywords": content.get("visual_keywords", []),
                "emotion": content.get("emotion", "neutral"),
                "scene_id": i + 1
            })
    
    # Sonuç cümlesi için gereksinim
    if "conclusion" in structured_content:
        media_requirements.append({
            "text": structured_content["conclusion"],
            "media_type": "video",  # Sonuç için video tercih ediyoruz
            "keywords": ["conclusion", "ending", structured_content.get("topic", "education")],
            "scene_id": len(media_requirements)
        })
    
    return media_requirements

def fetch_smart_media(media_requirements: List[Dict[str, Any]], pexels_api_key: str, project_folder: str, openai_api_key: str = None) -> Dict[str, List[str]]:
    """
    Gereksinimler doğrultusunda video ve fotoğraf indirir
    
    Args:
        media_requirements (List[Dict[str, Any]]): Medya gereksinimleri
        pexels_api_key (str): Pexels API anahtarı
        project_folder (str): Proje klasörünün yolu
        openai_api_key (str, optional): OpenAI API anahtarı, thumbnail analizinde kullanılacak
    
    Returns:
        Dict[str, List[str]]: İndirilen medya dosyalarının yolları
    """
    if not pexels_api_key:
        logger.error("Pexels API anahtarı bulunamadı!")
        return {"videos": [], "photos": []}
    
    # Medya dosyalarını saklayacak klasörleri oluştur
    video_folder = os.path.join(project_folder, "pexels_videos")
    photo_folder = os.path.join(project_folder, "pexels_photos")
    temp_folder = os.path.join(project_folder, "temp_thumbnails")
    
    if not os.path.exists(video_folder):
        os.makedirs(video_folder)
    if not os.path.exists(photo_folder):
        os.makedirs(photo_folder)
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
    
    downloaded_media = {"videos": [], "photos": []}
    
    # Her gereksinim için uygun medyayı indir
    for req in media_requirements:
        try:
            media_type = req.get("media_type", "video").lower()
            keywords = req.get("keywords", [])
            scene_id = req.get("scene_id", 0)
            scene_text = req.get("text", "")
            
            if not keywords:
                logger.warning(f"Sahne {scene_id} için anahtar kelimeler bulunamadı, varsayılanlar kullanılıyor")
                keywords = ["landscape", "nature", "education"]
            
            logger.info(f"Sahne {scene_id} için {media_type} aranıyor: {', '.join(keywords)}")
            
            # Her anahtar kelime için arama yap
            for keyword_index, keyword in enumerate(keywords):
                if media_type == "video":
                    # Video ara ve thumbnailleri analiz et
                    video_path = search_analyze_download_video(keyword, pexels_api_key, openai_api_key, 
                                                             video_folder, temp_folder, scene_id, 
                                                             keyword_index, scene_text)
                    if video_path:
                        downloaded_media["videos"].append(video_path)
                        logger.info(f"Sahne {scene_id} için video indirildi: {os.path.basename(video_path)}")
                        break  # Her sahne için bir video yeterli
                else:
                    # Fotoğraf ara ve thumbnailleri analiz et
                    photo_path = search_analyze_download_photo(keyword, pexels_api_key, openai_api_key, 
                                                             photo_folder, temp_folder, scene_id, 
                                                             keyword_index, scene_text)
                    if photo_path:
                        downloaded_media["photos"].append(photo_path)
                        logger.info(f"Sahne {scene_id} için fotoğraf indirildi: {os.path.basename(photo_path)}")
                        break  # Her sahne için bir fotoğraf yeterli
                
                # API limitlerine uymak için bekleme
                time.sleep(1)
            
            # Hiç medya bulunamazsa, hata kaydı
            if (media_type == "video" and not any(f"scene_{scene_id}" in v for v in downloaded_media["videos"])) or \
               (media_type == "photo" and not any(f"scene_{scene_id}" in p for p in downloaded_media["photos"])):
                logger.error(f"Sahne {scene_id} için {media_type} bulunamadı!")
        
        except Exception as e:
            logger.error(f"Sahne {scene_id} için medya indirme hatası: {str(e)}")
    
    # İndirilen medyaların listesini kaydet
    save_media_list_to_file(downloaded_media, project_folder)
    
    # Geçici klasörü temizle
    try:
        shutil.rmtree(temp_folder)
    except:
        pass
    
    return downloaded_media

def search_analyze_download_video(keyword: str, pexels_api_key: str, openai_api_key: str, 
                                video_folder: str, temp_folder: str, scene_id: int, 
                                keyword_index: int, scene_text: str) -> str:
    """
    Pexels'de video arar, thumbnailleri analiz eder ve en uygun olanı indirir
    
    Args:
        keyword (str): Arama anahtar kelimesi
        pexels_api_key (str): Pexels API anahtarı
        openai_api_key (str): OpenAI API anahtarı
        video_folder (str): İndirilecek klasör
        temp_folder (str): Geçici thumbnail klasörü
        scene_id (int): Sahne ID'si
        keyword_index (int): Anahtar kelime dizinindeki sırası
        scene_text (str): Sahne metni
    
    Returns:
        str: İndirilen video dosyasının yolu
    """
    # API isteği gönder
    headers = {"Authorization": pexels_api_key}
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=10&orientation=portrait"
    
    try:
        logger.info(f"Pexels API'ye video isteği gönderiliyor: {keyword}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"API hatası: {response.status_code} - {response.text}")
            return ""
        
        data = response.json()
        
        if "videos" not in data or not data["videos"]:
            logger.warning(f"'{keyword}' için video bulunamadı")
            return ""
        
        # Thumbnail analizi yap ve videoları sırala
        videos = data["videos"]
        logger.info(f"'{keyword}' için {len(videos)} video bulundu, thumbnail analizi yapılıyor...")
        
        analyzed_videos = batch_analyze_thumbnails(videos, scene_text, temp_folder, openai_api_key)
        
        # En uygun video yok mu kontrol et
        if not analyzed_videos:
            logger.warning(f"'{keyword}' için analiz edilebilir video bulunamadı")
            return ""
        
        # En yüksek puanlı videoyu indir (maksimum 3 deneme)
        max_attempts = min(3, len(analyzed_videos))
        
        for i in range(max_attempts):
            try:
                video = analyzed_videos[i]
                relevance_score = video.get("relevance_score", 0)
                
                # Çok düşük puanlı videoları atlama
                if relevance_score < 3 and i > 0:
                    logger.warning(f"Video uyum puanı çok düşük ({relevance_score}/10), arama atlanıyor")
                    continue
                
                # Dikey videoları tercih et
                video_files = video.get("video_files", [])
                portrait_videos = [v for v in video_files if v.get("width", 0) < v.get("height", 0)]
                
                if not portrait_videos:
                    portrait_videos = video_files
                
                if not portrait_videos:
                    logger.warning(f"'{keyword}' için kullanılabilir video formatı bulunamadı")
                    continue
                
                # Çözünürlüğe göre sırala (en yüksek başta)
                portrait_videos.sort(key=lambda x: x.get("width", 0) * x.get("height", 0), reverse=True)
                video_url = portrait_videos[0].get("link")
                
                if not video_url:
                    logger.warning(f"'{keyword}' için video URL'si bulunamadı")
                    continue
                
                # Dosya adını belirle ve indir
                video_path = os.path.join(video_folder, f"scene_{scene_id}_keyword_{keyword_index}_{keyword}.mp4")
                
                # Analiz sonucunu da dosya adına ekle
                if "analysis" in video and "suggested_camera_movement" in video["analysis"]:
                    camera_movement = video["analysis"]["suggested_camera_movement"]
                    video_path = os.path.join(video_folder, f"scene_{scene_id}_keyword_{keyword_index}_{keyword}_cam_{camera_movement}.mp4")
                
                # İndir
                logger.info(f"Video indiriliyor (uyum puanı: {relevance_score}/10): {video_url[:50]}...")
                local_filename = download_file(video_url, video_path)
                
                if local_filename:
                    logger.info(f"Video başarıyla indirildi: {local_filename}")
                    return local_filename
                
            except Exception as e:
                logger.error(f"Video işleme hatası: {str(e)}")
        
        logger.warning(f"'{keyword}' için hiçbir video indirilemedi")
        return ""
        
    except Exception as e:
        logger.error(f"Pexels video API hatası: {str(e)}")
        return ""

def search_analyze_download_photo(keyword: str, pexels_api_key: str, openai_api_key: str, 
                                photo_folder: str, temp_folder: str, scene_id: int, 
                                keyword_index: int, scene_text: str) -> str:
    """
    Pexels'de fotoğraf arar, thumbnailleri analiz eder ve en uygun olanı indirir
    
    Args:
        keyword (str): Arama anahtar kelimesi
        pexels_api_key (str): Pexels API anahtarı
        openai_api_key (str): OpenAI API anahtarı
        photo_folder (str): İndirilecek klasör
        temp_folder (str): Geçici thumbnail klasörü
        scene_id (int): Sahne ID'si
        keyword_index (int): Anahtar kelime dizinindeki sırası
        scene_text (str): Sahne metni
    
    Returns:
        str: İndirilen fotoğraf dosyasının yolu
    """
    # API isteği gönder
    headers = {"Authorization": pexels_api_key}
    url = f"https://api.pexels.com/v1/search?query={keyword}&per_page=10&orientation=portrait"
    
    try:
        logger.info(f"Pexels API'ye fotoğraf isteği gönderiliyor: {keyword}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"API hatası: {response.status_code} - {response.text}")
            return ""
        
        data = response.json()
        
        if "photos" not in data or not data["photos"]:
            logger.warning(f"'{keyword}' için fotoğraf bulunamadı")
            return ""
        
        # Thumbnail analizi yap ve fotoğrafları sırala
        photos = data["photos"]
        logger.info(f"'{keyword}' için {len(photos)} fotoğraf bulundu, thumbnail analizi yapılıyor...")
        
        # Önce fotoğrafları, thumbnail analizi için video formatına dönüştür
        photos_for_analysis = []
        for photo in photos:
            photos_for_analysis.append({
                "id": photo.get("id", ""),
                "image": photo.get("src", {}).get("medium", ""),  # Thumbnail olarak kullan
                "src": photo.get("src", {})
            })
        
        analyzed_photos = batch_analyze_thumbnails(photos_for_analysis, scene_text, temp_folder, openai_api_key)
        
        # En uygun fotoğraf yok mu kontrol et
        if not analyzed_photos:
            logger.warning(f"'{keyword}' için analiz edilebilir fotoğraf bulunamadı")
            return ""
        
        # En yüksek puanlı fotoğrafı indir (maksimum 3 deneme)
        max_attempts = min(3, len(analyzed_photos))
        
        for i in range(max_attempts):
            try:
                photo = analyzed_photos[i]
                relevance_score = photo.get("relevance_score", 0)
                
                # Çok düşük puanlı fotoğrafları atlama
                if relevance_score < 3 and i > 0:
                    logger.warning(f"Fotoğraf uyum puanı çok düşük ({relevance_score}/10), arama atlanıyor")
                    continue
                
                # Yüksek çözünürlüklü portre fotoğrafını al
                photo_url = photo.get("src", {}).get("portrait")
                
                if not photo_url:
                    photo_url = photo.get("src", {}).get("large2x")
                
                if not photo_url:
                    logger.warning(f"'{keyword}' için fotoğraf URL'si bulunamadı")
                    continue
                
                # Dosya adını belirle ve indir
                photo_path = os.path.join(photo_folder, f"scene_{scene_id}_keyword_{keyword_index}_{keyword}.jpg")
                
                # Analiz sonucunu da dosya adına ekle
                if "analysis" in photo and "suggested_camera_movement" in photo["analysis"]:
                    camera_movement = photo["analysis"]["suggested_camera_movement"]
                    photo_path = os.path.join(photo_folder, f"scene_{scene_id}_keyword_{keyword_index}_{keyword}_cam_{camera_movement}.jpg")
                
                # İndir
                logger.info(f"Fotoğraf indiriliyor (uyum puanı: {relevance_score}/10): {photo_url[:50]}...")
                local_filename = download_file(photo_url, photo_path)
                
                if local_filename:
                    logger.info(f"Fotoğraf başarıyla indirildi: {local_filename}")
                    return local_filename
                
            except Exception as e:
                logger.error(f"Fotoğraf işleme hatası: {str(e)}")
        
        logger.warning(f"'{keyword}' için hiçbir fotoğraf indirilemedi")
        return ""
        
    except Exception as e:
        logger.error(f"Pexels fotoğraf API hatası: {str(e)}")
        return ""

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
        logger.error(f"Dosya indirme hatası: {str(e)}")
        # Geçici dosyayı temizle
        if os.path.exists(destination + ".temp"):
            os.remove(destination + ".temp")
        return ""

def save_media_list_to_file(media_data: Dict[str, List[str]], project_folder: str) -> None:
    """
    İndirilen medya listesini dosyaya kaydeder
    
    Args:
        media_data (Dict[str, List[str]]): İndirilen medya bilgileri
        project_folder (str): Proje klasörünün yolu
    """
    try:
        media_info_file = os.path.join(project_folder, "media_list.json")
        
        # JSON formatında kaydet
        with open(media_info_file, "w", encoding="utf-8") as f:
            json.dump(media_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Medya listesi kaydedildi: {media_info_file}")
    except Exception as e:
        logger.error(f"Medya listesi kaydetme hatası: {str(e)}")

def select_optimal_media(storyboard: Dict[str, Any], media_files: Dict[str, List[str]], api_key: str) -> Dict[str, Any]:
    """
    Storyboard'a göre mevcut medyaları optimize eder
    
    Args:
        storyboard (Dict[str, Any]): Storyboard bilgileri
        media_files (Dict[str, List[str]]): İndirilen medya dosyaları
        api_key (str): OpenAI API anahtarı
    
    Returns:
        Dict[str, Any]: Optimizasyon sonuçları
    """
    # Her sahne için bir medya ata
    if not api_key:
        logger.warning("OpenAI API anahtarı bulunamadı, basit eşleme kullanılacak")
        return create_simple_media_mapping(storyboard, media_files)
    
    # OpenAI API'sini kullanarak akıllı eşleme yap (Daha gelişmiş versiyonda)
    return create_smart_media_mapping(storyboard, media_files)

def extract_camera_movement_from_filename(filename: str) -> str:
    """
    Dosya adından kamera hareketini çıkarır
    
    Args:
        filename (str): Dosya adı
    
    Returns:
        str: Kamera hareketi
    """
    try:
        if "_cam_" in filename:
            parts = filename.split("_cam_")
            if len(parts) > 1:
                return parts[1].split(".")[0]
    except:
        pass
    
    return "static"

def create_smart_media_mapping(storyboard: Dict[str, Any], media_files: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Akıllı medya eşleme stratejisi uygular
    
    Args:
        storyboard (Dict[str, Any]): Storyboard bilgileri
        media_files (Dict[str, List[str]]): İndirilen medya dosyaları
    
    Returns:
        Dict[str, Any]: Eşleme sonuçları
    """
    scenes = []
    videos = media_files.get("videos", [])
    photos = media_files.get("photos", [])
    
    if "scenes" not in storyboard:
        logger.error("Geçerli bir storyboard bulunamadı!")
        return {"scenes": []}
    
    # Her sahne için bir medya ata
    for i, scene in enumerate(storyboard["scenes"]):
        scene_data = {
            "scene_id": i,
            "text": scene.get("text", ""),
            "duration": scene.get("duration", 5),
            "transitions": scene.get("transitions", "fade"),
            "camera_movement": scene.get("camera_movement", "static")
        }
        
        # Sahneye uygun bir video bul
        matching_video = None
        for video in videos:
            if f"scene_{i}" in video:
                matching_video = video
                # Dosya adından kamera hareketini al
                camera_movement = extract_camera_movement_from_filename(video)
                if camera_movement and camera_movement != "static":
                    scene_data["camera_movement"] = camera_movement
                break
        
        # Eğer video bulunamazsa, fotoğraf ara
        if not matching_video:
            for photo in photos:
                if f"scene_{i}" in photo:
                    scene_data["media_file"] = photo
                    scene_data["media_type"] = "photo"
                    # Dosya adından kamera hareketini al
                    camera_movement = extract_camera_movement_from_filename(photo)
                    if camera_movement and camera_movement != "static":
                        scene_data["camera_movement"] = camera_movement
                    break
        else:
            scene_data["media_file"] = matching_video
            scene_data["media_type"] = "video"
        
        # Eğer hiçbir medya bulunamazsa varsayılan bir mesaj ekle
        if "media_file" not in scene_data:
            logger.warning(f"Sahne {i} için uygun medya bulunamadı!")
            
            # Varsa herhangi bir medyayı kullan
            if videos:
                scene_data["media_file"] = videos[0]
                scene_data["media_type"] = "video"
            elif photos:
                scene_data["media_file"] = photos[0]
                scene_data["media_type"] = "photo"
            else:
                scene_data["media_file"] = ""
                scene_data["media_type"] = "none"
        
        scenes.append(scene_data)
    
    return {"scenes": scenes}

def create_simple_media_mapping(storyboard: Dict[str, Any], media_files: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Basit bir medya eşleme stratejisi uygular
    
    Args:
        storyboard (Dict[str, Any]): Storyboard bilgileri
        media_files (Dict[str, List[str]]): İndirilen medya dosyaları
    
    Returns:
        Dict[str, Any]: Eşleme sonuçları
    """
    # Smart media mapping ile aynı şeyi yapıyoruz, ancak gelecekte genişletmek için ayrı tutuyoruz
    return create_smart_media_mapping(storyboard, media_files) 