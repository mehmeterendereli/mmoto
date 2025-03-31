#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
from typing import Dict, List, Any
from openai import OpenAI

logger = logging.getLogger('merak_makinesi')

def load_api_key() -> str:
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

def generate_structured_content(topic: str) -> Dict[str, Any]:
    """
    Detaylı ve yapılandırılmış içerik üretir
    
    Args:
        topic (str): İçerik konusu
    
    Returns:
        Dict[str, Any]: Yapılandırılmış içerik bilgileri
    """
    api_key = load_api_key()
    
    if not api_key:
        logger.error("OpenAI API anahtarı bulunamadı!")
        # Dummy içerik döndür
        return {
            "topic": topic,
            "introduction": f"{topic} hakkında bilgilendirici bir video.",
            "main_content": [
                {
                    "text": f"{topic} hakkında örnek cümle 1.",
                    "media_type": "video",
                    "visual_keywords": ["example", "sample", "demo"],
                    "emotion": "neutral",
                    "duration": 5
                }
            ],
            "conclusion": "Bilgilendirici video için teşekkürler.",
            "theme": {"style": "simple", "colors": ["blue", "white"]},
            "soundtrack_mood": "inspiring"
        }
    
    try:
        prompt = f"""
        '{topic}' hakkında kısa bir bilgilendirici video için detaylı ve yapılandırılmış bir içerik tasarla.
        
        İŞLEV:
        - Bu içerik, video akışının temelini oluşturacak ve her bölüm için doğru görsel türünü belirleyecek
        - İçerik doğrudan, öğretici ve ilgi çekici olmalı
        
        YAPILANDIRILMIŞ ÇIKTI FORMATI (JSON):
        1. Bir 'introduction' bölümü (1 cümle)
        2. 'main_content' dizisi (5 cümle) - her cümle için:
           - 'text': Cümle metni
           - 'media_type': Her cümle için ideal medya türü ('video' veya 'photo')
           - 'visual_keywords': 2-3 arama anahtar kelimesi (İngilizce)
           - 'emotion': Bu içerik için ideal duygu/atmosfer
           - 'duration': Tavsiye edilen süre (saniye olarak)
        3. Bir 'conclusion' bölümü (1 cümle)
        4. Tüm video için 'theme' önerisi (renk şeması, görsel stil)
        5. 'soundtrack_mood': Video için müzik/ses atmosferi önerisi
        
        Tüm metin Türkçe olmalı, anahtar kelimeler İngilizce olmalı.
        Toplam metin 45-50 saniyede seslendirilebilir olmalı.
        """
        
        # GPT-4o kullanarak yapılandırılmış içerik üret
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Sen bir yapay zeka video içerik tasarımcısısın. İçerik planlaması, görsel seçimi ve video akışı konusunda uzmansın."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        structured_content = json.loads(response.choices[0].message.content)
        logger.info(f"Yapılandırılmış içerik başarıyla oluşturuldu: {topic}")
        
        # İçerik bilgilerini dosyaya kaydet
        save_content_to_file(structured_content, topic)
        
        return structured_content
    
    except Exception as e:
        logger.error(f"Yapılandırılmış içerik üretme hatası: {str(e)}")
        return {
            "topic": topic,
            "introduction": f"{topic} hakkında bir içerik oluşturulamadı.",
            "main_content": [
                {
                    "text": "İçerik üretiminde bir hata oluştu.",
                    "media_type": "photo",
                    "visual_keywords": ["error", "problem", "issue"],
                    "emotion": "neutral",
                    "duration": 5
                }
            ],
            "conclusion": "Lütfen daha sonra tekrar deneyin.",
            "theme": {"style": "simple", "colors": ["gray", "white"]},
            "soundtrack_mood": "neutral"
        }

def create_visual_storyboard(structured_content: Dict[str, Any]) -> Dict[str, Any]:
    """
    İçerik için görsel hikaye akışı oluşturur
    
    Args:
        structured_content (Dict[str, Any]): Yapılandırılmış içerik bilgileri
    
    Returns:
        Dict[str, Any]: Görsel hikaye akışı
    """
    api_key = load_api_key()
    
    if not api_key:
        logger.error("OpenAI API anahtarı bulunamadı!")
        # Basit bir storyboard döndür
        return create_default_storyboard(structured_content)
    
    try:
        prompt = f"""
        Aşağıdaki içerik için detaylı bir görsel hikaye akışı (storyboard) oluştur:
        
        {json.dumps(structured_content, ensure_ascii=False)}
        
        GÖREV:
        - Her bölüm için ideal görsel geçişler, kamera hareketleri öner
        - Altyazı konumlandırması ve efektleri belirle
        - Görsel vurgulama noktalarını işaretle
        - Her sahne için yönerge ver
        
        ÇIKTI FORMATI (JSON):
        1. Videonun her bölümü için ayrı bir nesne içeren "scenes" dizisi:
           - "text": Metin içeriği
           - "visuals": Görsel detaylar (ne gösterileceği, nasıl gösterileceği)
           - "transitions": Önceki ve sonraki sahneye geçiş efektleri
           - "text_effects": Altyazı efektleri ve konumlandırma
           - "duration": Sahne süresi
           - "camera_movement": Varsa önerilen kamera hareketi
        2. "theme": Genel görsel tema detayları
        3. "color_scheme": Ana renk şeması 
        4. "music_suggestion": Müzik/ses önerisi
        """
        
        # GPT-4o kullanarak görsel hikaye akışı oluştur
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Sen bir profesyonel video storyboard uzmanısın. Görsel hikaye anlatımı, kamera hareketleri ve video geçişleri konusunda deneyimlisin."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        storyboard = json.loads(response.choices[0].message.content)
        logger.info("Görsel hikaye akışı başarıyla oluşturuldu")
        
        # Storyboard'ı dosyaya kaydet
        save_storyboard_to_file(storyboard, structured_content.get("topic", "unknown"))
        
        return storyboard
    
    except Exception as e:
        logger.error(f"Storyboard oluşturma hatası: {str(e)}")
        return create_default_storyboard(structured_content)

def create_default_storyboard(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Basit bir varsayılan storyboard oluşturur
    
    Args:
        content (Dict[str, Any]): İçerik bilgileri
    
    Returns:
        Dict[str, Any]: Basit storyboard
    """
    scenes = []
    
    # Giriş sahnesi
    if "introduction" in content:
        scenes.append({
            "text": content["introduction"],
            "visuals": "Konuyla ilgili genel görüntü",
            "transitions": "Fade in",
            "text_effects": "Alt orta konumda büyüyerek beliren metin",
            "duration": 5,
            "camera_movement": "Sabit"
        })
    
    # Ana içerik sahneleri
    if "main_content" in content:
        for i, item in enumerate(content["main_content"]):
            scenes.append({
                "text": item["text"],
                "visuals": f"İçerikle ilgili {item['media_type']}",
                "transitions": "Cross dissolve",
                "text_effects": "Alt orta konumda beyaz metin",
                "duration": item.get("duration", 7),
                "camera_movement": "Yavaş zoom" if i % 2 == 0 else "Sabit"
            })
    
    # Sonuç sahnesi
    if "conclusion" in content:
        scenes.append({
            "text": content["conclusion"],
            "visuals": "Kapanış görüntüsü",
            "transitions": "Fade out",
            "text_effects": "Alt orta konumda yavaşça kaybolan metin",
            "duration": 5,
            "camera_movement": "Yavaş uzaklaşma"
        })
    
    return {
        "scenes": scenes,
        "theme": content.get("theme", {"style": "simple", "colors": ["blue", "white"]}),
        "color_scheme": ["#3A86FF", "#FFFFFF", "#172A3A"],
        "music_suggestion": content.get("soundtrack_mood", "inspiring")
    }

def save_content_to_file(content: Dict[str, Any], topic: str) -> None:
    """
    Üretilen içeriği dosyaya kaydeder
    
    Args:
        content (Dict[str, Any]): Üretilen içerik
        topic (str): Konu
    """
    try:
        # Proje klasörünü bul
        project_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_folder = os.path.join(project_folder, "output")
        
        # En son oluşturulan klasörü bul
        folders = [f for f in os.listdir(output_folder) if os.path.isdir(os.path.join(output_folder, f))]
        if folders:
            latest_folder = max(folders, key=lambda x: os.path.getctime(os.path.join(output_folder, x)))
            project_folder = os.path.join(output_folder, latest_folder)
            
            # İçeriği JSON olarak kaydet
            with open(os.path.join(project_folder, "structured_content.json"), "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Yapılandırılmış içerik kaydedildi: {project_folder}/structured_content.json")
    except Exception as e:
        logger.error(f"İçerik kaydetme hatası: {str(e)}")

def save_storyboard_to_file(storyboard: Dict[str, Any], topic: str) -> None:
    """
    Storyboard'ı dosyaya kaydeder
    
    Args:
        storyboard (Dict[str, Any]): Storyboard
        topic (str): Konu
    """
    try:
        # Proje klasörünü bul
        project_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_folder = os.path.join(project_folder, "output")
        
        # En son oluşturulan klasörü bul
        folders = [f for f in os.listdir(output_folder) if os.path.isdir(os.path.join(output_folder, f))]
        if folders:
            latest_folder = max(folders, key=lambda x: os.path.getctime(os.path.join(output_folder, x)))
            project_folder = os.path.join(output_folder, latest_folder)
            
            # Storyboard'ı JSON olarak kaydet
            with open(os.path.join(project_folder, "visual_storyboard.json"), "w", encoding="utf-8") as f:
                json.dump(storyboard, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Görsel hikaye akışı kaydedildi: {project_folder}/visual_storyboard.json")
    except Exception as e:
        logger.error(f"Storyboard kaydetme hatası: {str(e)}") 