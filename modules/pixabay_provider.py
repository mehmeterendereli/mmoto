#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import asyncio
import aiohttp
import aiofiles
import json
import base64
import shutil
from typing import List, Dict, Any, Tuple, Optional

from modules.video_provider import VideoProvider
from utils.shell_utils import is_windows

class PixabayProvider(VideoProvider):
    """
    Pixabay API üzerinden video sağlama hizmeti
    """
    
    def __init__(self, api_key: str, openai_api_key: str):
        """
        Pixabay sağlayıcısını başlat
        
        Args:
            api_key (str): Pixabay API anahtarı
            openai_api_key (str): OpenAI API anahtarı
        """
        self.api_key = api_key
        self.openai_api_key = openai_api_key
    
    async def translate_keywords_to_english(self, keywords: List[str], source_language: str = "tr") -> List[str]:
        """
        Anahtar kelimeleri İngilizce'ye çevirir
        
        Args:
            keywords (List[str]): Çevrilecek anahtar kelimeler
            source_language (str): Kaynak dil kodu
            
        Returns:
            List[str]: İngilizce anahtar kelimeler
        """
        # API anahtarı boşsa, çeviri yapmadan kelimeyi aynen döndür
        if not self.openai_api_key or not keywords:
            return keywords
        
        try:
            # Kelimeler zaten İngilizceyse çevirme
            if source_language == "en":
                return keywords
                
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
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
                    model="gpt-4o-mini",
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
                
                # Eğer satır sayısı anahtar kelime sayısından farklıysa, virgülle de ayır
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
    
    async def search_videos(self, keywords: List[str], topic: str, content: List[str], language: str = "tr") -> List[Dict[str, Any]]:
        """
        Pixabay API kullanarak anahtar kelimelere göre video arar
        
        Args:
            keywords (List[str]): Aranacak anahtar kelimeler
            topic (str): Video konusu
            content (List[str]): Video içeriği
            language (str): Dil kodu
            
        Returns:
            List[Dict[str, Any]]: Video bilgilerini içeren liste
        """
        if not self.api_key:
            print("Uyarı: Pixabay API anahtarı boş!")
            return []
        
        all_videos = []
        
        # Anahtar kelimeleri İngilizce'ye çevir
        english_keywords = await self.translate_keywords_to_english(keywords, language)
        
        # Pixabay tarafından desteklenen dil kodlarını kontrol et
        pixabay_langs = ["cs", "da", "de", "en", "es", "fr", "id", "it", "hu", "nl", 
                         "no", "pl", "pt", "ro", "sk", "fi", "sv", "tr", "vi", "th", 
                         "bg", "ru", "el", "ja", "ko", "zh"]
        
        # Dili kontrol et, desteklenmiyorsa varsayılan dili kullan
        search_lang = language if language in pixabay_langs else "en"
        
        # Anahtar kelimeleri sınırla (ilk 4 anahtar kelimeyi kullan)
        limited_keywords = english_keywords[:4]
        limited_original_keywords = keywords[:4] if len(keywords) >= 4 else keywords
        
        print(f"Arama için kullanılan anahtar kelimeler (sınırlı): {', '.join(limited_keywords)}")
        
        # Her anahtar kelime için asenkron arama yap
        async with aiohttp.ClientSession() as session:
            search_tasks = []
            
            for i, keyword in enumerate(limited_keywords):
                # Boş anahtar kelimeleri atla
                if not keyword.strip():
                    continue
                
                # URL kodlama ile kelimedeki boşlukları + ile değiştir
                encoded_keyword = keyword.replace(' ', '+')
                    
                # Pixabay API URL'sini oluştur - doğru parametrelerle ve daha az video döndür
                url = (
                    f"https://pixabay.com/api/videos/?key={self.api_key}"
                    f"&q={encoded_keyword}"
                    f"&lang={search_lang}"
                    f"&per_page=10"  # Her anahtar kelime için 20 yerine 10 video getir
                    f"&safesearch=true"
                )
                
                # Orijinal (çevrilmemiş) anahtar kelimeyi de parametre olarak geçirelim
                original_keyword = limited_original_keywords[i] if i < len(limited_original_keywords) else keyword
                search_tasks.append(self.fetch_keyword_videos(session, url, keyword, original_keyword))
            
            # Tüm aramaları paralel olarak çalıştır
            keyword_results = await asyncio.gather(*search_tasks)
            
            # Sonuçları birleştir
            for result in keyword_results:
                all_videos.extend(result)
        
        # Video sayısını sınırla (en fazla 30 video ile devam et)
        if len(all_videos) > 30:
            print(f"Bulunan video sayısı çok fazla ({len(all_videos)}), 30 video ile devam ediliyor...")
            # Videoları rastgele sırala ve ilk 30'unu al
            import random
            random.shuffle(all_videos)
            all_videos = all_videos[:30]
        
        print(f"Toplam {len(all_videos)} adet potansiyel video bulundu.")
        return all_videos
        
    async def fetch_keyword_videos(self, session, url: str, keyword: str, original_keyword: str = None) -> List[Dict[str, Any]]:
        """
        Belirli bir anahtar kelime için video arar
        
        Args:
            session: aiohttp oturumu
            url (str): Arama URL'si
            keyword (str): Aranan anahtar kelime (İngilizce)
            original_keyword (str): Orijinal anahtar kelime
            
        Returns:
            List[Dict[str, Any]]: Video bilgilerini içeren liste
        """
        videos = []
        try:
            display_keyword = original_keyword or keyword
            print(f"'{display_keyword}' için Pixabay API'ye istek gönderiliyor...")
            
            # URL parametrelerini Pixabay dökümanına göre iyileştir
            # 1. Sayfa başına 20 video (varsayılan)
            # 2. Güvenli arama aktif
            # 3. Video tipi tümü, en popüler olanları getir
            # 4. Kategoriyi otomatik belirle (doğal sonuçlar için)
            improved_url = f"{url}&safesearch=true&video_type=all&order=popular"
            
            async with session.get(improved_url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if "hits" in data and len(data["hits"]) > 0:
                        found_videos = data["hits"]
                        print(f"{display_keyword} için {len(found_videos)} adet video bulundu")
                        
                        # Her video için metadata bilgilerini ekle
                        for i, video in enumerate(found_videos):
                            # Pixabay dökümantasyonuna göre thumbnail URL'si videos nesnesi altında
                            # Her boyut için ayrı bir thumbnail var, medium boyutu kullanıyoruz
                            videos_data = video.get("videos", {})
                            
                            # Thumbnail URL'sini videos altındaki ilgili boyuttan al
                            thumbnail_url = None
                            if "medium" in videos_data and "thumbnail" in videos_data["medium"]:
                                thumbnail_url = videos_data["medium"]["thumbnail"]
                            elif "small" in videos_data and "thumbnail" in videos_data["small"]:
                                thumbnail_url = videos_data["small"]["thumbnail"]
                            elif "tiny" in videos_data and "thumbnail" in videos_data["tiny"]:
                                thumbnail_url = videos_data["tiny"]["thumbnail"]
                            
                            # Thumbnail yoksa kullanıcı profil resmi veya başka bir alternatif kullan
                            if not thumbnail_url:
                                thumbnail_url = video.get("userImageURL")
                            
                            # Farklı video formatları ve çözünürlükler
                            video_sources = {}
                            
                            # Video formatlarını ve çözünürlüklerini kontrol et
                            for format_type in ["large", "medium", "small", "tiny"]:
                                if format_type in videos_data:
                                    video_info = videos_data[format_type]
                                    if video_info and "url" in video_info:
                                        width = video_info.get("width", 0)
                                        height = video_info.get("height", 0)
                                        video_sources[format_type] = {
                                            "url": video_info["url"],
                                            "width": width,
                                            "height": height
                                        }
                            
                            # Eğer kullanılabilir video kaynağı varsa
                            if video_sources and thumbnail_url:
                                # Dikey videoları (portrait) tercih et
                                portrait_sources = {}
                                for format_type, source in video_sources.items():
                                    if source["height"] > source["width"]:
                                        portrait_sources[format_type] = source
                                
                                # Eğer dikey video yoksa, tüm kaynakları kullan
                                if not portrait_sources:
                                    portrait_sources = video_sources
                                
                                # Çözünürlüğe göre en yüksek olanı bul
                                best_source = None
                                max_resolution = 0
                                
                                for format_type, source in portrait_sources.items():
                                    resolution = source["width"] * source["height"]
                                    if resolution > max_resolution:
                                        max_resolution = resolution
                                        best_source = source
                                
                                if best_source:
                                    videos.append({
                                        "id": f"pixabay_{video.get('id', i)}",
                                        "thumbnail_url": thumbnail_url,
                                        "video_url": best_source["url"],
                                        "width": best_source["width"],
                                        "height": best_source["height"],
                                        "duration": video.get("duration", 0),
                                        "provider": "pixabay",
                                        "keyword": display_keyword,
                                        "tags": video.get("tags", "")  # Anahtar kelimeler için yararlı olabilir
                                    })
                    else:
                        print(f"'{display_keyword}' için sonuç bulunamadı!")
                else:
                    print(f"API hatası: {response.status} - {await response.text()}")
        except Exception as e:
            print(f"Video arama hatası ({display_keyword}): {str(e)}")
        
        return videos
        
    async def download_thumbnail(self, session, video_info: Dict[str, Any], temp_folder: str) -> Tuple[Dict[str, Any], Optional[str]]:
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
        
        # URL'den dosya uzantısını belirle
        import urllib.parse
        from pathlib import Path
        
        # URL'yi parse et ve yolunu al
        parsed_url = urllib.parse.urlparse(thumbnail_url)
        path = parsed_url.path
        
        # Uzantıyı al
        ext = Path(path).suffix.lower()
        
        # Eğer uzantı yoksa veya geçersizse .jpg kullan
        if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            ext = '.jpg'
        
        # Thumbnail dosya yolunu oluştur
        thumbnail_path = os.path.join(temp_folder, f"thumb_{video_info['id']}{ext}")
        
        try:
            async with session.get(thumbnail_url, timeout=30) as response:
                if response.status == 200:
                    # Thumbnail'i kaydet
                    content_type = response.headers.get('Content-Type', '')
                    
                    # Content-Type'a göre uygun uzantıyı belirle
                    if 'jpeg' in content_type or 'jpg' in content_type:
                        new_ext = '.jpg'
                    elif 'png' in content_type:
                        new_ext = '.png'
                    elif 'gif' in content_type:
                        new_ext = '.gif'
                    elif 'webp' in content_type:
                        new_ext = '.webp'
                    else:
                        new_ext = ext  # URL'den alınan uzantıyı kullan
                    
                    # Eğer Content-Type'a göre uzantı değiştiyse, dosya yolunu güncelle
                    if new_ext != ext:
                        thumbnail_path = os.path.join(temp_folder, f"thumb_{video_info['id']}{new_ext}")
                    
                    # Dosyayı kaydet
                    async with aiofiles.open(thumbnail_path, 'wb') as f:
                        await f.write(await response.read())
                    
                    # Eğer format desteklenmiyorsa, jpeg'e dönüştür
                    try:
                        from PIL import Image
                        img = Image.open(thumbnail_path)
                        
                        # Eğer format desteklenmiyorsa veya webp ise jpeg'e dönüştür
                        if img.format not in ['JPEG', 'PNG', 'GIF'] or new_ext == '.webp':
                            jpeg_path = os.path.join(temp_folder, f"thumb_{video_info['id']}.jpg")
                            img = img.convert('RGB')  # RGBA formatını RGB'ye dönüştür
                            img.save(jpeg_path, 'JPEG')
                            
                            # Orijinal dosyayı sil ve jpeg yolunu döndür
                            if jpeg_path != thumbnail_path:
                                os.remove(thumbnail_path)
                                thumbnail_path = jpeg_path
                    except Exception as img_error:
                        print(f"Resim dönüştürme hatası: {str(img_error)}")
                    
                    return video_info, thumbnail_path
        except Exception as e:
            print(f"Thumbnail indirme hatası: {str(e)}")
        
        return video_info, None
        
    async def evaluate_thumbnail_relevance(self, video_info: Dict[str, Any], topic: str, content: List[str]) -> Tuple[Dict[str, Any], float]:
        """
        GPT-4o-mini kullanarak thumbnail'in konu ile alakasını değerlendirir
        
        Args:
            video_info (Dict[str, Any]): Video bilgileri (thumbnail_url içermeli)
            topic (str): Ana konu
            content (List[str]): İçerik metni
            
        Returns:
            Tuple[Dict[str, Any], float]: Video bilgileri ve alaka puanı (0-10)
        """
        try:
            # Thumbnail URL'sini kontrol et
            thumbnail_url = video_info.get("thumbnail_url")
            if not thumbnail_url:
                print(f"Thumbnail URL bulunamadı: {video_info.get('id', 'bilinmeyen')}")
                return video_info, 0.0
            
            # İçerik metnini string'e dönüştür (maksimum 500 karakter)
            content_text = "\n".join(content)[:500]
            
            # Dil kontrolü - İngilizce mi Türkçe mi?
            # İngilizce soru işaretleri genellikle İngilizce başlıklarda kullanılır
            is_english = any(word in topic.lower() for word in ["what", "why", "how", "if", "can", "do", "is", "are", "will", "would"]) or "?" in topic
            
            # OpenAI API'yi çağır
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            # İlgililik değerlendirme isteği
            system_message = """You are an AI assistant that evaluates how relevant an image is to a given topic and content.
            Rate the relevance on a scale from 0 to 10, where:
            - 0 means completely irrelevant
            - 10 means perfectly relevant and ideal for the topic
            Your response should be in this format: "[SCORE]: [BRIEF EXPLANATION]"
            For example: "7.5: The image shows [relevant content] which relates well to the topic."
            """
            
            # Dile göre user message oluştur
            if is_english:
                user_message = f"""Rate how relevant this image is to the following topic and content on a scale from 0-10:
                
                TOPIC: {topic}
                
                CONTENT: 
                {content_text}...
                
                Remember to respond with just "[SCORE]: [BRIEF EXPLANATION]"
                """
            else:
                user_message = f"""Bu görselin aşağıdaki konu ve içerikle ne kadar alakalı olduğunu 0-10 arası bir puanla değerlendir:
                
                KONU: {topic}
                
                İÇERİK: 
                {content_text}...
                
                Sadece "[PUAN]: [KISA AÇIKLAMA]" formatında cevap ver.
                """
            
            # API'ye istek gönder - doğrudan thumbnail URL'sini kullanarak
            try:
                # API isteği
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_message},
                        {
                            "role": "user", 
                            "content": [
                                {"type": "text", "text": user_message},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": thumbnail_url,
                                        "detail": "low"
                                    }
                                }
                            ]
                        }
                    ],
                    temperature=0.7,
                    max_tokens=100
                )
                
                response_text = response.choices[0].message.content
                
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
                    
                    # [ ] karakterlerini temizle
                    score_text = score_text.replace("[", "").replace("]", "")
                    
                    # Puanı dönüştür
                    score = float(score_text)
                    
                    # Puan 0-10 arasında olmalı
                    score = max(0.0, min(10.0, score))
                    
                    print(f"Thumbnail puanı: {score}/10 - {video_info.get('keyword', 'bilinmeyen')}")
                    return video_info, score
                except Exception as parse_error:
                    # Puan çıkarılamazsa varsayılan değer
                    print(f"Puan çıkarılamadı: {response_text} - Hata: {str(parse_error)}")
                    return video_info, 5.0  # Hata durumunda orta seviye puan ver
            except Exception as api_error:
                print(f"OpenAI API Hatası: {str(api_error)}")
                # API hatası durumunda varsayılan puan ver - video indirmenin devam etmesini sağlar
                return video_info, 5.0
                
        except Exception as e:
            print(f"Thumbnail değerlendirme hatası: {str(e)}")
            # Hata durumunda varsayılan puan ver
            return video_info, 5.0

    async def evaluate_thumbnails_batch(self, videos: List[Dict[str, Any]], topic: str, content: List[str], batch_size: int = 20) -> List[Tuple[Dict[str, Any], float]]:
        """
        Birden fazla thumbnail'ı toplu olarak değerlendirir
        
        Args:
            videos (List[Dict[str, Any]]): Video bilgileri listesi (her biri thumbnail_url içermeli)
            topic (str): Ana konu
            content (List[str]): İçerik metni
            batch_size (int): Bir istek içinde değerlendirilecek maksimum thumbnail sayısı
            
        Returns:
            List[Tuple[Dict[str, Any], float]]: Video bilgileri ve ilgili puanlar
        """
        if not videos:
            return []
            
        # İçerik metnini string'e dönüştür (maksimum 500 karakter)
        content_text = "\n".join(content)[:500]
        
        # Dil kontrolü
        is_english = any(word in topic.lower() for word in ["what", "why", "how", "if", "can", "do", "is", "are", "will", "would"]) or "?" in topic
        
        # OpenAI API'yi çağır
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_api_key)
        
        # Base mesajlar
        system_message = """You are an AI assistant that evaluates how relevant images are to a given topic and content.
        For EACH image, rate its relevance on a scale from 0 to 10 where 0 is completely irrelevant and 10 is perfectly relevant.
        Your response format should be a numbered list, one score per image:
        1. [SCORE]: Brief explanation
        2. [SCORE]: Brief explanation
        ...and so on.
        """
        
        # Dile göre user message başlangıcı
        if is_english:
            user_message_intro = f"""Rate how relevant EACH of the following images is to this topic and content (0-10 scale):
            
            TOPIC: {topic}
            
            CONTENT: 
            {content_text}...
            
            For EACH image, give a numbered rating in this format:
            1. [SCORE]: brief explanation
            2. [SCORE]: brief explanation
            etc.
            """
        else:
            user_message_intro = f"""Aşağıdaki HER BİR görselin bu konu ve içerikle ne kadar alakalı olduğunu puanla (0-10 ölçeği):
            
            KONU: {topic}
            
            İÇERİK: 
            {content_text}...
            
            HER BİR görsel için numaralı bir puanlama yap:
            1. [PUAN]: kısa açıklama
            2. [PUAN]: kısa açıklama
            vs.
            """
        
        # İşlenmiş sonuçlar
        results = []
        
        # Videoları batch_size kadar gruplara ayırma
        for i in range(0, len(videos), batch_size):
            batch = videos[i:i+batch_size]
            print(f"Toplu değerlendirme: {i+1}-{i+len(batch)}/{len(videos)} arası thumbnaillar işleniyor...")
            
            # Batch içindeki thumbnail URL'leri
            batch_urls = [v.get("thumbnail_url") for v in batch if v.get("thumbnail_url")]
            
            # Batch boşsa devam et
            if not batch_urls:
                continue
            
            # Mesaj içeriği oluştur
            content_array = [{"type": "text", "text": user_message_intro}]
            
            # Her bir thumbnail URL'sini ekle
            for idx, url in enumerate(batch_urls, 1):
                # Görsel URL'sini ekle
                content_array.append({
                    "type": "image_url",
                    "image_url": {
                        "url": url,
                        "detail": "low"
                    }
                })
            
            try:
                # API isteği
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": content_array}
                    ],
                    temperature=0.7,
                    max_tokens=500  # Daha fazla thumbnail için gerekli token sayısı
                )
                
                response_text = response.choices[0].message.content
                
                # Yanıtı satırlara ayır
                lines = [line.strip() for line in response_text.split('\n') if line.strip()]
                
                # Her bir satırı işle (her satır bir görsel için puan içermeli)
                processed_count = 0
                for line in lines:
                    if processed_count >= len(batch):
                        break
                        
                    # Satır numaralı formatta olmalı: "1. [SCORE]: ..."
                    if '.' in line:
                        try:
                            # Numarayı at
                            after_number = line.split('.', 1)[1].strip()
                            
                            # Puanı bul - farklı formatlara uygun olacak şekilde
                            # Format 1: "1. [7.5]: Açıklama"
                            # Format 2: "1. 7.5: Açıklama"
                            # Format 3: "1. **7.5**: Açıklama"
                            
                            # Yıldız işaretlerini kaldır
                            cleaned_text = after_number.replace('*', '')
                            
                            # Köşeli parantezleri kaldır
                            cleaned_text = cleaned_text.replace('[', '').replace(']', '')
                            
                            # İki nokta üstü varsa, ilk kısmı al
                            if ':' in cleaned_text:
                                score_text = cleaned_text.split(':', 1)[0].strip()
                            else:
                                # İki nokta üstü yoksa, ilk sayıyı bul
                                import re
                                score_match = re.search(r'\b(\d+(\.\d+)?)\b', cleaned_text)
                                if score_match:
                                    score_text = score_match.group(1)
                                else:
                                    raise ValueError(f"Score not found in line: {line}")
                            
                            # Puanı dönüştür
                            score = float(score_text)
                            # Puan 0-10 arasında olmalı
                            score = max(0.0, min(10.0, score))
                            
                            # İlgili video bilgisini ve puanı ekle
                            video_info = batch[processed_count]
                            print(f"Thumbnail puanı: {score}/10 - {video_info.get('keyword', 'bilinmeyen')}")
                            results.append((video_info, score))
                            processed_count += 1
                        except Exception as parse_error:
                            print(f"Puan çıkarılamadı: {line} - Hata: {str(parse_error)}")
                            # Varsayılan değeri ekle ve devam et
                            if processed_count < len(batch):
                                results.append((batch[processed_count], 5.0))
                                processed_count += 1
                
                # Eğer beklenen sayıda puan çıkarılamazsa, kalan videoları varsayılan değerle doldur
                while processed_count < len(batch):
                    print(f"Eksik puan değerlendirmesi, varsayılan puan atanıyor: {batch[processed_count].get('keyword', 'bilinmeyen')}")
                    results.append((batch[processed_count], 5.0))
                    processed_count += 1
                    
            except Exception as e:
                print(f"Toplu değerlendirme hatası: {str(e)}")
                # Hata durumunda tüm batch için varsayılan puan ver
                for video_info in batch:
                    results.append((video_info, 5.0))
        
        return results
            
    async def download_video(self, video_url: str, destination: str) -> str:
        """
        Belirtilen URL'den video dosyasını indirir
        
        Args:
            video_url (str): İndirilecek video URL'si
            destination (str): Hedef dosya yolu
            
        Returns:
            str: İndirilen dosya yolu veya boş string
        """
        try:
            # İndirme klasörünü oluştur
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            # İndirme işlemi
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url, timeout=180) as response:
                    if response.status == 200:
                        # Dosyaya kaydet
                        temp_file = destination + ".temp"
                        async with aiofiles.open(temp_file, 'wb') as f:
                            await f.write(await response.read())
                        
                        # Temp dosyayı asıl dosyaya taşı
                        import shutil
                        shutil.move(temp_file, destination)
                        
                        print(f"Video başarıyla indirildi: {destination}")
                        return destination
                    else:
                        print(f"Video indirme hatası: HTTP {response.status}")
            
            return ""
        except Exception as e:
            print(f"Video indirme hatası: {str(e)}")
            # Geçici dosyayı temizle
            if os.path.exists(destination + ".temp"):
                os.remove(destination + ".temp")
            return ""
            
    async def download_videos(self, videos: List[Dict[str, Any]], project_folder: str, min_score: float = 5.0) -> List[str]:
        """
        Videoları indir ve değerlendirme puanına göre sırala
        
        Args:
            videos (List[Dict[str, Any]]): İndirilecek video bilgileri
            project_folder (str): Proje klasörü
            min_score (float): Minimum kabul edilebilir puan
            
        Returns:
            List[str]: İndirilen video dosyalarının yolları
        """
        if not videos:
            print("İndirilecek video bulunamadı!")
            return []
            
        # Video klasörü - Pixabay için yeni klasör
        video_folder = os.path.join(project_folder, "pixabay_videos")
        os.makedirs(video_folder, exist_ok=True)
        
        # Eğer çok fazla video varsa, değerlendirme için en fazla 20 video seç
        max_videos_to_evaluate = 20
        if len(videos) > max_videos_to_evaluate:
            print(f"Çok fazla video var ({len(videos)}), değerlendirme için {max_videos_to_evaluate} video seçiliyor...")
            import random
            # Videoları rastgele sırala
            random_videos = videos.copy()
            random.shuffle(random_videos)
            filtered_videos = random_videos[:max_videos_to_evaluate]
        else:
            filtered_videos = videos
        
        print(f"Toplam {len(filtered_videos)} video değerlendirilecek")
        
        # İçerik bilgisi yoksa boş liste döndür
        if not hasattr(self, 'topic') or not hasattr(self, 'content'):
            print("İçerik bilgisi bulunamadı!")
            return []
            
        # Thumbnailleri toplu olarak değerlendir (batch_size=20)
        evaluation_results = await self.evaluate_thumbnails_batch(filtered_videos, self.topic, self.content, batch_size=20)
        
        # Değerlendirilen videoları puanlara göre eşleştir
        scored_videos = []
        for video_info, score in evaluation_results:
            video_info["score"] = score
            scored_videos.append(video_info)
        
        # Puanı yeterli olan videoları filtrele
        high_scored_videos = [v for v in scored_videos if v["score"] >= min_score]
        
        # Eğer yeterli video bulunamazsa minimum puanı düşür
        if len(high_scored_videos) < 3:
            lower_min_score = min(min_score * 0.7, 3.0)  # Minimum puanı %30 düşür, en az 3.0 olsun
            print(f"Yeterli video bulunamadı, minimum puanı {min_score} → {lower_min_score} olarak düşürüyorum.")
            high_scored_videos = [v for v in scored_videos if v["score"] >= lower_min_score]
            
            # Hala yeterli video yoksa, tüm pozitif puanlı videoları al
            if len(high_scored_videos) < 2:
                print("Hala yeterli video yok, tüm pozitif puanlı videoları kullanıyorum.")
                high_scored_videos = [v for v in scored_videos if v["score"] > 0]
        
        # Puanlara göre sırala (en yüksek önce)
        high_scored_videos.sort(key=lambda x: x["score"], reverse=True)
        
        print(f"Minimum puan üzerinde {len(high_scored_videos)} video bulundu:")
        for i, video in enumerate(high_scored_videos[:10]):  # En iyi 10 videoyu göster
            print(f"{i+1}. Video ({video['keyword']}): Puan {video['score']}/10")
        
        # En iyi videoları indir (en fazla 5 adet)
        download_limit = min(5, len(high_scored_videos))
        videos_to_download = high_scored_videos[:download_limit]
        
        if not videos_to_download:
            print("İndirilecek uygun video bulunamadı!")
            return []
        
        # Videoları asenkron olarak indir
        download_tasks = []
        for i, video in enumerate(videos_to_download):
            video_path = os.path.join(video_folder, f"video_{video['keyword']}_{i+1}.mp4")
            download_tasks.append(self.download_video(video["video_url"], video_path))
        
        downloaded_videos = await asyncio.gather(*download_tasks)
        
        # Boş olmayan yolları filtrele
        successful_downloads = [path for path in downloaded_videos if path]
        
        return successful_downloads
        
    async def fetch_videos(self, keywords: List[str], topic: str, content: List[str], 
                          project_folder: str, min_score: float = 5.0, 
                          language: str = "tr") -> List[str]:
        """
        Anahtar kelimelere göre video ara ve indir
        
        Args:
            keywords (List[str]): Aranacak anahtar kelimeler
            topic (str): Video konusu
            content (List[str]): Video içeriği
            project_folder (str): Proje klasörü
            min_score (float): Minimum kabul edilebilir puan
            language (str): Dil kodu
            
        Returns:
            List[str]: İndirilen video dosyalarının yolları
        """
        # İçerik bilgisini sınıf attribute'larına kaydet (download_videos için gerekli)
        self.topic = topic
        self.content = content
        
        # API anahtarlarını kontrol et
        if not self.api_key:
            print("Uyarı: Pixabay API anahtarı boş!")
            return []
        
        if not self.openai_api_key:
            print("Uyarı: OpenAI API anahtarı boş!")
            return []
            
        # Videoları ara
        videos = await self.search_videos(keywords, topic, content, language)
        
        if not videos:
            print("Hiç video bulunamadı!")
            return []
            
        # Videoları indir
        return await self.download_videos(videos, project_folder, min_score) 