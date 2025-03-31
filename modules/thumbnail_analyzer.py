#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import requests
import base64
import logging
from typing import Dict, List, Any
from openai import OpenAI

logger = logging.getLogger('merak_makinesi')

def load_openai_api_key() -> str:
    """
    config.json dosyasından OpenAI API anahtarını yükler
    
    Returns:
        str: OpenAI API anahtarı
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("openai_api_key", "")
        except Exception as e:
            logger.error(f"API anahtarı yükleme hatası: {str(e)}")
    
    return ""

def download_thumbnail(thumbnail_url: str, temp_folder: str) -> str:
    """
    Thumbnail görselini indirir
    
    Args:
        thumbnail_url (str): Thumbnail URL'si
        temp_folder (str): Geçici klasör yolu
    
    Returns:
        str: İndirilen thumbnail'in dosya yolu
    """
    try:
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
            
        # Benzersiz dosya adı oluştur
        file_name = os.path.join(temp_folder, f"thumbnail_{hash(thumbnail_url) % 10000}.jpg")
        
        # Thumbnail'i indir
        response = requests.get(thumbnail_url, stream=True, timeout=10)
        response.raise_for_status()
        
        with open(file_name, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return file_name
    
    except Exception as e:
        logger.error(f"Thumbnail indirme hatası: {str(e)}")
        return ""

def encode_image_to_base64(image_path: str) -> str:
    """
    Görseli base64'e çevirir
    
    Args:
        image_path (str): Görsel dosya yolu
    
    Returns:
        str: Base64 kodlu görsel
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Base64 kodlama hatası: {str(e)}")
        return ""

def analyze_thumbnail_with_gpt4o(thumbnail_base64: str, scene_text: str, api_key: str) -> Dict[str, Any]:
    """
    GPT-4o ile thumbnail'i analiz eder
    
    Args:
        thumbnail_base64 (str): Base64 kodlu thumbnail görsel
        scene_text (str): Sahne metni
        api_key (str): OpenAI API anahtarı
    
    Returns:
        Dict[str, Any]: Analiz sonuçları
    """
    try:
        # GPT-4o API prompt hazırlama
        prompt = f"""
        Bir video için thumbnail görüntüsü incelemeni istiyorum. Bu video, aşağıdaki metin için görsel olarak kullanılacak:

        "{scene_text}"

        Lütfen bu görseli analiz et ve şu bilgileri JSON formatında döndür:
        1. relevance_score: Görselin metinle ne kadar alakalı olduğunu 1-10 arası puanla
        2. relevance_reasoning: Neden bu puanı verdiğinin kısa açıklaması
        3. main_elements: Görselde gördüğün ana unsurlar
        4. mood: Görselin genel atmosferi/duygusu
        5. suggested_camera_movement: Bu görsel için önerilen kamera hareketi (static, zoom_in, zoom_out, pan_left, pan_right, ken_burns)

        Lütfen sadece JSON formatında cevap ver.
        """

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "Sen bir görsel içerik analisti ve video editörüsün. Görselleri inceleyip içerikle uyumunu değerlendirirsin."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{thumbnail_base64}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # JSON yanıtı ayrıştır
        analysis_result = json.loads(response.choices[0].message.content)
        
        return analysis_result
    
    except Exception as e:
        logger.error(f"GPT-4o thumbnail analiz hatası: {str(e)}")
        return {
            "relevance_score": 0,
            "relevance_reasoning": f"Analiz sırasında hata oluştu: {str(e)}",
            "main_elements": [],
            "mood": "unknown",
            "suggested_camera_movement": "static"
        }

def batch_analyze_thumbnails(video_results: List[Dict], scene_text: str, temp_folder: str, api_key: str = None) -> List[Dict]:
    """
    Bir grup video thumbnail'ini analiz eder
    
    Args:
        video_results (List[Dict]): Pexels API video sonuçları
        scene_text (str): Sahne metni
        temp_folder (str): Geçici klasör yolu
        api_key (str, optional): OpenAI API anahtarı. Belirtilmezse config.json'dan alınır.
    
    Returns:
        List[Dict]: Analiz edilmiş video sonuçları
    """
    if not api_key:
        api_key = load_openai_api_key()
    
    if not api_key:
        logger.error("OpenAI API anahtarı bulunamadı!")
        return video_results
    
    analyzed_videos = []
    
    for video in video_results:
        try:
            if "image" not in video:
                logger.warning("Video sonucunda thumbnail bulunamadı, atlıyorum")
                video["relevance_score"] = 0
                analyzed_videos.append(video)
                continue
            
            thumbnail_url = video["image"]
            
            # Thumbnail'i indir
            thumbnail_path = download_thumbnail(thumbnail_url, temp_folder)
            if not thumbnail_path:
                logger.warning(f"Thumbnail indirilemedi: {thumbnail_url}")
                video["relevance_score"] = 0
                analyzed_videos.append(video)
                continue
            
            # Base64'e çevir
            thumbnail_base64 = encode_image_to_base64(thumbnail_path)
            if not thumbnail_base64:
                logger.warning(f"Thumbnail base64'e çevrilemedi: {thumbnail_path}")
                video["relevance_score"] = 0
                analyzed_videos.append(video)
                continue
            
            # GPT-4o ile analiz et
            analysis = analyze_thumbnail_with_gpt4o(thumbnail_base64, scene_text, api_key)
            
            # Video nesnesine analiz sonuçlarını ekle
            video.update({
                "analysis": analysis,
                "relevance_score": analysis.get("relevance_score", 0),
                "suggested_camera_movement": analysis.get("suggested_camera_movement", "static")
            })
            
            analyzed_videos.append(video)
            
            # Geçici dosyayı sil
            try:
                os.remove(thumbnail_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Video thumbnail analizi hatası: {str(e)}")
            video["relevance_score"] = 0
            analyzed_videos.append(video)
    
    # Videolar uyum puanına göre sırala (en yüksek başta)
    analyzed_videos.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    return analyzed_videos 