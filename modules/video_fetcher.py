#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import requests
import time
import shutil
import json
import base64
import asyncio
import aiohttp
import aiofiles
from typing import List, Dict, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI
from utils.shell_utils import run_command, is_windows

# Eski fonksiyonlar yorum satırına alındı
"""
def fetch_videos(keywords: List[str], api_key: str, project_folder: str) -> List[str]:
    '''
    Pexels API kullanarak anahtar kelimelere göre video arar ve indirir
    
    Args:
        keywords (List[str]): Aranacak anahtar kelimeler
        api_key (str): Pexels API anahtarı
        project_folder (str): Proje klasörünün yolu
    
    Returns:
        List[str]: İndirilen video dosyalarının yolları
    '''
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
    '''
    Belirtilen URL'den dosyayı güvenli bir şekilde indirir
    
    Args:
        url (str): İndirilecek dosyanın URL'si
        destination (str): Kaydedilecek dosyanın yolu
    
    Returns:
        str: İndirilen dosyanın yolu veya hata durumunda boş string
    '''
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
"""

# Anahtar kelimeleri İngilizce'ye çeviren fonksiyon
async def translate_keywords_to_english(keywords: List[str], openai_api_key: str, source_language: str = "tr") -> List[str]:
    """
    Anahtar kelimeleri İngilizce'ye çevirir
    
    Args:
        keywords (List[str]): Çevrilecek anahtar kelimeler
        openai_api_key (str): OpenAI API anahtarı
        source_language (str): Kaynak dil kodu (örn. "tr", "es")
    
    Returns:
        List[str]: İngilizce anahtar kelimeler
    """
    # API anahtarı boşsa, çeviri yapmadan kelimeyi aynen döndür
    if not openai_api_key or not keywords:
        return keywords
    
    try:
        # Kelimeler zaten İngilizceyse çevirme
        if source_language == "en":
            return keywords
            
        client = OpenAI(api_key=openai_api_key)
        
        # İlk olarak kaynak dili tanımla
        language_names = {
            "tr": "Turkish",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ar": "Arabic",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean"
        }
        
        source_lang_name = language_names.get(source_language, "unknown")
        
        # Çeviri isteği için prompt
        prompt = f"""
        Translate the following {source_lang_name} keywords to English. 
        Return ONLY the translated keywords in their simplest form, one per line.
        No explanations or extra text.

        Keywords: {', '.join(keywords)}
        """
        
        # API isteği
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a translator that accurately translates keywords."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            # Yanıtı işle
            translated_text = response.choices[0].message.content.strip()
            
            # Satırlara ayır ve her birini temizle
            translated_keywords = [line.strip() for line in translated_text.split("\n") if line.strip()]
            
            # Eğer satır sayısı anahtar kelime sayısından farklıysa, virgülle de ayır (bazen API satır yerine virgül kullanabilir)
            if len(translated_keywords) != len(keywords):
                comma_split = [k.strip() for k in translated_text.replace(",", "\n").split("\n") if k.strip()]
                if len(comma_split) == len(keywords):
                    translated_keywords = comma_split
            
            # Eğer çeviri başarılıysa, anahtar kelime sayısı ile çeviri sayısı eşit olmalı
            if len(translated_keywords) == len(keywords):
                print(f"Anahtar kelimeler İngilizce'ye çevrildi: {', '.join(keywords)} -> {', '.join(translated_keywords)}")
                return translated_keywords
            else:
                print(f"Çeviri sonucu anahtar kelime sayısı uyumsuz: {len(keywords)} girdi, {len(translated_keywords)} çıktı")
                # Basit bir çözüm: ilk "len(keywords)" kadar çeviriyi al
                if len(translated_keywords) > len(keywords):
                    return translated_keywords[:len(keywords)]
                # Veya eksik kısımları orijinal kelimelerle tamamla
                elif len(translated_keywords) < len(keywords):
                    return translated_keywords + keywords[len(translated_keywords):]
                
        except Exception as e:
            print(f"Çeviri hatası: {str(e)}")
            # Hata durumunda orijinal kelimeleri döndür
            return keywords
            
    except Exception as e:
        print(f"Çeviri hatası: {str(e)}")
        return keywords  # Hata durumunda orijinal kelimeleri döndür

# Yeni asenkron arama fonksiyonu - dil parametresi eklendi
async def search_videos_by_keywords(keywords: List[str], api_key: str, openai_api_key: str = "", language: str = "tr", per_page: int = 5) -> List[Dict[str, Any]]:
    """
    Pexels API kullanarak anahtar kelimelere göre video arar ve thumbnail bilgilerini döndürür
    
    Args:
        keywords (List[str]): Aranacak anahtar kelimeler
        api_key (str): Pexels API anahtarı
        openai_api_key (str): OpenAI API anahtarı (çeviri için)
        language (str): Anahtar kelimelerin dili (default: "tr")
        per_page (int): Her aramada dönecek video sayısı
    
    Returns:
        List[Dict[str, Any]]: Video bilgilerini içeren liste
    """
    if not api_key:
        print("Uyarı: Pexels API anahtarı boş!")
        return []
    
    all_videos = []
    headers = {"Authorization": api_key}
    
    # Anahtar kelimeler zaten İngilizce'den gelecek şekilde düzenlenecek
    # Bu satırı yine de eski kod uyumluluğu için koruyoruz
    english_keywords = keywords
    
    # Her anahtar kelime için asenkron arama yap
    async with aiohttp.ClientSession() as session:
        search_tasks = []
        
        for i, keyword in enumerate(english_keywords):
            # Boş anahtar kelimeleri atla
            if not keyword.strip():
                continue
                
            url = f"https://api.pexels.com/videos/search?query={keyword}&per_page={per_page}"
            # Orijinal (çevrilmemiş) anahtar kelimeyi de parametre olarak geçirelim
            original_keyword = keywords[i] if i < len(keywords) else keyword
            search_tasks.append(fetch_keyword_videos(session, url, headers, keyword, original_keyword))
        
        # Tüm aramaları paralel olarak çalıştır
        keyword_results = await asyncio.gather(*search_tasks)
        
        # Sonuçları birleştir
        for result in keyword_results:
            all_videos.extend(result)
    
    print(f"Toplam {len(all_videos)} adet potansiyel video bulundu.")
    return all_videos

async def fetch_keyword_videos(session, url: str, headers: Dict[str, str], keyword: str, original_keyword: str = None) -> List[Dict[str, Any]]:
    """
    Belirli bir anahtar kelime için video arar
    
    Args:
        session: aiohttp oturumu
        url (str): Arama URL'si
        headers (Dict[str, str]): API başlıkları
        keyword (str): Aranan anahtar kelime (İngilizce)
        original_keyword (str): Orijinal anahtar kelime
    
    Returns:
        List[Dict[str, Any]]: Video bilgilerini içeren liste
    """
    videos = []
    try:
        display_keyword = original_keyword or keyword
        print(f"'{display_keyword}' için Pexels API'ye istek gönderiliyor...")
        async with session.get(url, headers=headers, timeout=30) as response:
            if response.status == 200:
                data = await response.json()
                
                if "videos" in data and len(data["videos"]) > 0:
                    found_videos = data["videos"]
                    print(f"{display_keyword} için {len(found_videos)} adet video bulundu")
                    
                    # Her video için metadata bilgilerini ekle
                    for i, video in enumerate(found_videos):
                        # Video thumbnail URL'si kontrolü
                        thumbnail_url = video.get("image")
                        if thumbnail_url:
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
                                    # Video bilgilerini sakla
                                    video_info = {
                                        "id": video.get("id"),
                                        "keyword": display_keyword,
                                        "thumbnail_url": thumbnail_url,
                                        "video_url": video_url,
                                        "width": portrait_videos[0].get("width"),
                                        "height": portrait_videos[0].get("height"),
                                        "duration": video.get("duration"),
                                        "index": i
                                    }
                                    videos.append(video_info)
                else:
                    print(f"'{display_keyword}' için sonuç bulunamadı!")
            else:
                error_text = await response.text()
                print(f"API hatası: {response.status} - {error_text}")
    except Exception as e:
        print(f"Video arama hatası ({display_keyword}): {str(e)}")
    
    return videos

async def download_thumbnail(session, video_info: Dict[str, Any], temp_folder: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Video thumbnail'ini indirir
    
    Args:
        session: aiohttp oturumu
        video_info (Dict[str, Any]): Video bilgileri
        temp_folder (str): Geçici klasör yolu
    
    Returns:
        Tuple[Dict[str, Any], Optional[str]]: Video bilgileri ve thumbnail dosyasının yolu
    """
    thumbnail_url = video_info.get("thumbnail_url")
    if not thumbnail_url:
        return video_info, None
    
    thumbnail_path = os.path.join(temp_folder, f"thumb_{video_info['id']}.jpg")
    
    try:
        async with session.get(thumbnail_url, timeout=30) as response:
            if response.status == 200:
                # Thumbnail'i kaydet
                async with aiofiles.open(thumbnail_path, 'wb') as f:
                    await f.write(await response.read())
                return video_info, thumbnail_path
    except Exception as e:
        print(f"Thumbnail indirme hatası: {str(e)}")
    
    return video_info, None

async def evaluate_thumbnail_relevance(thumbnail_path: str, topic: str, content: List[str], openai_api_key: str) -> Tuple[str, float]:
    """
    GPT-4o kullanarak thumbnail'in konu ile alakasını değerlendirir
    
    Args:
        thumbnail_path (str): Thumbnail dosya yolu
        topic (str): Ana konu
        content (List[str]): İçerik metni
        openai_api_key (str): OpenAI API anahtarı
    
    Returns:
        Tuple[str, float]: Thumbnail yolu ve alaka puanı (0-10)
    """
    try:
        # Thumbnail dosyasını base64 formatına dönüştür
        with open(thumbnail_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # İçerik metnini string'e dönüştür
        content_text = "\n".join(content)
        
        # Dil kontrolü - İngilizce mi Türkçe mi?
        # İngilizce soru işaretleri genellikle İngilizce başlıklarda kullanılır
        is_english = any(word in topic.lower() for word in ["what", "why", "how", "if", "can", "do", "is", "are", "will", "would"]) or "?" in topic
        
        # OpenAI API'yi çağır
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai_api_key}"
        }
        
        # İngilizce veya Türkçe prompt
        if is_english:
            system_content = "Rate how relevant this image is to the given topic and content on a scale of 0-10. Only provide a score and a short explanation."
            user_text = f"Topic: {topic}\n\nContent: {content_text}\n\nRate how relevant this image is to the topic and content on a scale of 0-10. Only return the score and a brief explanation. Format: [SCORE]: [EXPLANATION]"
        else:
            system_content = "Bu görselin verilen konu ve içerikle ne kadar alakalı olduğunu 0-10 arasında değerlendir. Sadece puan ve kısa bir açıklama ver."
            user_text = f"Konu: {topic}\n\nİçerik: {content_text}\n\nBu görselin konuyla ve içerikle alakasını 0-10 arasında puanla. Sadece puanı ve kısa açıklamayı döndür. Format: [PUAN]: [AÇIKLAMA]"
        
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system", 
                    "content": system_content
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_text
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 150
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    response_text = result["choices"][0]["message"]["content"]
                    
                    # Yanıttan puanı çıkar
                    try:
                        # "[PUAN]: [AÇIKLAMA]" veya "[SCORE]: [EXPLANATION]" formatında yanıt bekliyoruz
                        # Önce iki nokta üstüne göre ayır
                        if ":" in response_text:
                            score_text = response_text.split(":")[0].strip()
                        # Eğer iki nokta üstü yoksa, ilk sayıyı bulmaya çalış
                        else:
                            import re
                            score_match = re.search(r'\b(\d+(\.\d+)?)\b', response_text)
                            if score_match:
                                score_text = score_match.group(1)
                            else:
                                raise ValueError("Score not found in response")
                        
                        # Puanı dönüştür
                        score = float(score_text)
                        
                        # Puan 0-10 arasında olmalı
                        score = max(0.0, min(10.0, score))
                        
                        print(f"Thumbnail puanı: {score}/10 - {thumbnail_path}")
                        return thumbnail_path, score
                    except Exception as parse_error:
                        # Puan çıkarılamazsa varsayılan değer
                        print(f"Puan çıkarılamadı: {response_text} - Hata: {str(parse_error)}")
                        return thumbnail_path, 0.0
                else:
                    error_text = await response.text()
                    print(f"GPT-4o API hatası: {response.status} - {error_text}")
                    return thumbnail_path, 0.0
    except Exception as e:
        print(f"Thumbnail değerlendirme hatası: {str(e)}")
        return thumbnail_path, 0.0

async def download_video(video_url: str, destination: str) -> str:
    """
    Belirtilen URL'den videoyu asenkron olarak indirir
    
    Args:
        video_url (str): Video URL'si
        destination (str): Kaydedilecek dosya yolu
    
    Returns:
        str: İndirilen dosya yolu veya boş string
    """
    temp_file = destination + ".temp"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(video_url, timeout=300) as response:
                if response.status == 200:
                    # Geçici dosyaya kaydet
                    async with aiofiles.open(temp_file, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    
                    # Geçici dosyayı hedef dosyaya taşı
                    shutil.move(temp_file, destination)
                    print(f"Video başarıyla indirildi: {destination}")
                    return destination
                else:
                    print(f"Video indirme hatası - HTTP {response.status}")
                    return ""
    except Exception as e:
        print(f"Video indirme hatası: {str(e)}")
        # Geçici dosyayı temizle
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return ""

# Ana video arama fonksiyonu - dil parametresi eklendi
async def fetch_videos(keywords: List[str], pexels_api_key: str, openai_api_key: str, topic: str, content: List[str], 
                       project_folder: str, min_score: float = 5.0, language: str = "tr") -> List[str]:
    """
    Pexels API kullanarak anahtar kelimelere göre video arar ve indirir
    Her video için OpenAI API ile ilgi düzeyi değerlendirmesi yapar
    
    Args:
        keywords (List[str]): Aranacak anahtar kelimeler
        pexels_api_key (str): Pexels API anahtarı
        openai_api_key (str): OpenAI API anahtarı
        topic (str): Video konusu
        content (List[str]): Video içeriği
        project_folder (str): Proje klasörünün yolu
        min_score (float): Minimum ilgi düzeyi puanı (0-10 arasında)
        language (str): Anahtar kelimelerin dili (default: "tr")
    
    Returns:
        List[str]: İndirilen video dosyalarının yolları
    """
    # Video klasörlerini oluştur
    video_folder = os.path.join(project_folder, "pexels_videos")
    os.makedirs(video_folder, exist_ok=True)
    
    # Thumbnail klasörü
    temp_folder = os.path.join(project_folder, "temp_thumbs")
    os.makedirs(temp_folder, exist_ok=True)
    
    # API anahtarlarını kontrol et
    if not pexels_api_key:
        print("Uyarı: Pexels API anahtarı boş!")
        return []
    
    if not openai_api_key:
        print("Uyarı: OpenAI API anahtarı boş!")
        return []
    
    # Videoları ara - İngilizce arama için dil kodunu gönder
    videos = await search_videos_by_keywords(keywords, pexels_api_key, openai_api_key, language)
    
    if not videos:
        print("Hiç video bulunamadı!")
        return []
    
    # Thumbnailleri indir
    async with aiohttp.ClientSession() as session:
        thumbnail_tasks = [download_thumbnail(session, video, temp_folder) for video in videos]
        thumbnail_results = await asyncio.gather(*thumbnail_tasks)
    
    # Başarılı thumbnail indirmelerini topla
    successful_thumbnails = [(video, thumb_path) for video, thumb_path in thumbnail_results if thumb_path]
    
    # Thumbnailleri değerlendir
    evaluation_tasks = [evaluate_thumbnail_relevance(thumb_path, topic, content, openai_api_key) 
                        for video, thumb_path in successful_thumbnails]
    evaluation_results = await asyncio.gather(*evaluation_tasks)
    
    # Thumbnailleri puanlara göre eşleştir
    scored_videos = []
    for i, (_, score) in enumerate(evaluation_results):
        if score >= min_score:
            video_info = successful_thumbnails[i][0]
            video_info["score"] = score
            scored_videos.append(video_info)
    
    # Puanlara göre sırala (en yüksek önce)
    scored_videos.sort(key=lambda x: x["score"], reverse=True)
    
    print(f"Minimum puan {min_score}/10 üzerinde {len(scored_videos)} video bulundu.")
    
    # En iyi videoları indir (en fazla 5 adet)
    download_limit = min(5, len(scored_videos))
    videos_to_download = scored_videos[:download_limit]
    
    # Videoları asenkron olarak indir
    download_tasks = []
    for i, video in enumerate(videos_to_download):
        video_path = os.path.join(video_folder, f"video_{video['keyword']}_{i+1}.mp4")
        download_tasks.append(download_video(video["video_url"], video_path))
    
    downloaded_videos = await asyncio.gather(*download_tasks)
    
    # Boş olmayan yolları filtrele
    successful_downloads = [path for path in downloaded_videos if path]
    
    # Geçici klasörü temizle
    try:
        shutil.rmtree(temp_folder)
    except Exception as e:
        print(f"Geçici klasör silme hatası: {str(e)}")
    
    # En az bir video indirildi mi kontrol et
    if not successful_downloads:
        print("Hiç video indirilemedi, varsayılan video kullanılacak...")
        # Buraya varsayılan video ekleme kodu gelebilir
    
    return successful_downloads
