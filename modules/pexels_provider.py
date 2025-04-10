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

def truncate_string(text: str, max_length: int = 4000) -> str:
    """
    Metni belirli bir uzunluğa kısaltır
    
    Args:
        text (str): Kısaltılacak metin
        max_length (int): Maksimum uzunluk
        
    Returns:
        str: Kısaltılmış metin
    """
    if not text:
        return ""
        
    if isinstance(text, list):
        text = "\n".join(text)
        
    if len(text) <= max_length:
        return text
        
    return text[:max_length-3] + "..."

class PexelsProvider(VideoProvider):
    """
    Pexels API üzerinden video sağlama hizmeti
    """
    
    def __init__(self, api_key: str, openai_api_key: str):
        """
        Pexels sağlayıcısını başlat
        
        Args:
            api_key (str): Pexels API anahtarı
            openai_api_key (str): OpenAI API anahtarı
        """
        self.api_key = api_key
        self.openai_api_key = openai_api_key
    
    def is_turkish_content(self, text: str) -> bool:
        """
        İçeriğin Türkçe olup olmadığını kontrol eder
        
        Args:
            text (str): Kontrol edilecek metin
            
        Returns:
            bool: İçerik Türkçe ise True, değilse False
        """
        if not text:
            return False
            
        # Türkçe'ye özgü karakterler
        turkish_chars = set("çğıöşüÇĞİÖŞÜ")
        
        # Metin içinde Türkçe karakter varsa
        if any(char in turkish_chars for char in text):
            return True
            
        # Türkçe'de sık kullanılan kelimeler
        turkish_common_words = ["ve", "ile", "bir", "bu", "için", "çok", "daha", 
                               "olarak", "gibi", "kadar", "sonra", "önce", "var", "yok"]
        
        # Metni küçük harfe çevir ve kelimelere ayır
        words = text.lower().split()
        
        # Türkçe yaygın kelimelerden en az 3 tanesi metinde varsa
        turkish_word_count = sum(1 for word in words if word in turkish_common_words)
        if turkish_word_count >= 3:
            return True
            
        return False
    
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
        Pexels API kullanarak anahtar kelimelere göre video arar
        
        Args:
            keywords (List[str]): Aranacak anahtar kelimeler
            topic (str): Video konusu
            content (List[str]): Video içeriği
            language (str): Dil kodu
            
        Returns:
            List[Dict[str, Any]]: Video bilgilerini içeren liste
        """
        if not self.api_key:
            print("Uyarı: Pexels API anahtarı boş!")
            return []
        
        all_videos = []
        headers = {"Authorization": self.api_key}
        
        # Anahtar kelimeleri İngilizce'ye çevir
        english_keywords = await self.translate_keywords_to_english(keywords, language)
        
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
                    
                # Her anahtar kelime için daha az video getir
                url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=10"
                # Orijinal (çevrilmemiş) anahtar kelimeyi de parametre olarak geçirelim
                original_keyword = limited_original_keywords[i] if i < len(limited_original_keywords) else keyword
                search_tasks.append(self.fetch_keyword_videos(session, url, headers, keyword, original_keyword))
            
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
        
    async def fetch_keyword_videos(self, session, url: str, headers: Dict[str, str], keyword: str, original_keyword: str = None) -> List[Dict[str, Any]]:
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
                                        videos.append({
                                            "id": f"pexels_{video.get('id', i)}",
                                            "thumbnail_url": thumbnail_url,
                                            "video_url": video_url,
                                            "width": portrait_videos[0].get("width", 0),
                                            "height": portrait_videos[0].get("height", 0),
                                            "duration": video.get("duration", 0),
                                            "provider": "pexels",
                                            "keyword": display_keyword
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
        
    async def evaluate_thumbnail_relevance(self, thumbnail_url: str, keyword: str, topic: str, content: str) -> float:
        """
        Thumbnail'ın konu ile ilgisi değerlendirilir
        
        Args:
            thumbnail_url (str): Değerlendirilecek thumbnail URL'si
            keyword (str): Arama anahtar kelimesi
            topic (str): İlgi konusu
            content (str): İçerik metni
            
        Returns:
            float: İlgi derecesi (0-10 arası)
        """
        # Thumbnail URL'si yoksa değerlendirme yapılamaz
        if not thumbnail_url:
            print("Thumbnail URL'si bulunamadı!")
            return 5.0  # Ortalama bir değer döndür
            
        try:
            # İçeriği işle ve sıkıştır
            processed_content = truncate_string(content, 4000)  # İçeriği sıkıştır (max 4000 karakter)
            
            # İçerik dilini belirle
            if self.is_turkish_content(processed_content):
                language = "Türkçe"
                query = """
                Bu video küçük resmi (thumbnail) verilen konuyla ne kadar alakalı? 0-10 arasında bir puan ver.
                Sadece puanı döndür, başka bir şey yazma.
                
                Konu: {topic}
                İçerik: {content}
                Aranan Kelime: {keyword}
                
                Puan (0-10):
                """
            else:
                language = "English"
                query = """
                How relevant is this video thumbnail to the given topic? Rate it from 0-10.
                Return only the score, don't write anything else.
                
                Topic: {topic}
                Content: {content}
                Search Term: {keyword}
                
                Score (0-10):
                """
                
            # API mesajını oluştur
            user_message = query.format(
                topic=topic,
                content=processed_content,
                keyword=keyword
            )
            
            messages = [
                {"role": "system", "content": f"You are an AI assistant evaluating the relevance of video thumbnails to a topic. The content is in {language}."},
                {"role": "user", "content": f"Here's the thumbnail URL I'm evaluating: {thumbnail_url}\n\n{user_message}"}
            ]
            
            # API isteği gönder
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip()
            # Sadece sayıyı ayıkla
            import re
            score_match = re.search(r'(\d+(\.\d+)?)', result)
            
            if score_match:
                score = float(score_match.group(1))
                # Skor aralığını kontrol et
                if score < 0:
                    score = 0.0
                elif score > 10:
                    score = 10.0
                    
                print(f"Thumbnail değerlendirme puanı: {score}/10 (keyword: {keyword})")
                return score
            else:
                print(f"Skor bulunamadı, varsayılan değer kullanılıyor. API yanıtı: {result}")
                return 5.0  # Varsayılan değer
                
        except Exception as e:
            print(f"Thumbnail değerlendirirken hata oluştu: {str(e)}")
            return 5.0  # Hata durumunda ortalama bir değer döndür
            
    async def evaluate_thumbnails_batch(self, videos: List[Dict[str, Any]], topic: str, content: List[str], batch_size: int = 20) -> List[Tuple[Dict[str, Any], float]]:
        """
        Bir grup thumbnail'ı toplu olarak değerlendirir
        
        Args:
            videos (List[Dict[str, Any]]): Değerlendirilecek video bilgileri listesi
            topic (str): İlgi konusu
            content (List[str]): İçerik metni
            batch_size (int): Bir seferde işlenecek thumbnail sayısı
            
        Returns:
            List[Tuple[Dict[str, Any], float]]: Video bilgisi ve ilgililik puanı çiftlerinin listesi
        """
        results = []
        
        # İçeriği işle ve sıkıştır
        if isinstance(content, list):
            content = "\n".join(content)
        processed_content = truncate_string(content, 4000)  # İçeriği sıkıştır (max 4000 karakter)
        
        # İçerik dilini belirle
        is_turkish = self.is_turkish_content(processed_content)
        language = "Türkçe" if is_turkish else "English"
        
        # Batch'ler halinde işle
        for i in range(0, len(videos), batch_size):
            batch = videos[i:i+batch_size]
            print(f"Thumbnail değerlendirme: Batch {i//batch_size + 1}/{(len(videos)-1)//batch_size + 1} işleniyor...")
            
            try:
                # Her thumbnail için API mesajı oluştur
                system_message = {"role": "system", "content": f"You are an AI assistant evaluating the relevance of multiple video thumbnails to a topic. The content is in {language}."}
                
                user_message_content = f"I need you to evaluate {len(batch)} video thumbnails and rate their relevance to the following topic on a scale of 0-10.\n\n"
                user_message_content += f"Topic: {topic}\n"
                user_message_content += f"Content: {processed_content}\n\n"
                
                for j, video in enumerate(batch):
                    thumbnail_url = video.get("thumbnail_url", "")
                    keyword = video.get("keyword", "")
                    user_message_content += f"Thumbnail {j+1} (Search term: {keyword}): {thumbnail_url}\n"
                
                if is_turkish:
                    user_message_content += "\nHer thumbnail için 0-10 arasında ilgililik puanı ver. Sadece puanları döndür, şu formatta: 'Thumbnail 1: 7.5, Thumbnail 2: 6.0,' vb."
                else:
                    user_message_content += "\nGive a relevance score from 0-10 for each thumbnail. Return only the scores in this format: 'Thumbnail 1: 7.5, Thumbnail 2: 6.0,' etc."
                
                user_message = {"role": "user", "content": user_message_content}
                
                # API isteği gönder
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[system_message, user_message],
                    max_tokens=100
                )
                
                result = response.choices[0].message.content.strip()
                
                # Yanıtı işle
                import re
                score_pattern = re.compile(r'Thumbnail\s*(\d+)\s*:\s*(\d+(\.\d+)?)', re.IGNORECASE)
                scores = score_pattern.findall(result)
                
                # Her thumbnail için sonuçları eşleştir
                if scores:
                    for score_match in scores:
                        thumbnail_index = int(score_match[0]) - 1
                        if 0 <= thumbnail_index < len(batch):
                            score = float(score_match[1])
                            # Skor aralığını kontrol et
                            if score < 0:
                                score = 0.0
                            elif score > 10:
                                score = 10.0
                                
                            results.append((batch[thumbnail_index], score))
                            print(f"Thumbnail {thumbnail_index+1} değerlendirme puanı: {score}/10 (keyword: {batch[thumbnail_index].get('keyword', '')})")
                        else:
                            print(f"Geçersiz thumbnail indeksi: {thumbnail_index+1}")
                else:
                    print(f"Skorlar bulunamadı, her thumbnail için varsayılan değer kullanılıyor. API yanıtı: {result}")
                    for video in batch:
                        results.append((video, 5.0))  # Varsayılan değer
                
            except Exception as e:
                print(f"Batch thumbnail değerlendirirken hata oluştu: {str(e)}")
                # Hata durumunda batch içindeki tüm videolar için varsayılan değer kullan
                for video in batch:
                    results.append((video, 5.0))
        
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
            
    async def download_videos(self, videos: List[Dict[str, Any]], project_folder: str, min_score: float = 5.0, batch_size: int = 3) -> List[str]:
        """
        Videoları indir ve değerlendirme puanına göre sırala
        
        Args:
            videos (List[Dict[str, Any]]): İndirilecek video bilgileri
            project_folder (str): Proje klasörü
            min_score (float): Minimum kabul edilebilir puan
            batch_size (int): Aynı anda indirilecek video sayısı
            
        Returns:
            List[str]: İndirilen video dosyalarının yolları
        """
        if not videos:
            print("İndirilecek video bulunamadı!")
            return []
            
        # Video klasörü
        video_folder = os.path.join(project_folder, "pexels_videos")
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
            
        # Thumbnailleri toplu olarak değerlendir
        evaluation_results = await self.evaluate_thumbnails_batch(filtered_videos, self.topic, self.content)
        
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
        
        # Videoları batch'ler halinde asenkron olarak indir
        successful_downloads = []
        for i in range(0, len(videos_to_download), batch_size):
            batch = videos_to_download[i:i+batch_size]
            download_tasks = []
            
            for j, video in enumerate(batch):
                video_path = os.path.join(video_folder, f"video_{video['keyword']}_{i+j+1}.mp4")
                download_tasks.append(self.download_video(video["video_url"], video_path))
            
            batch_results = await asyncio.gather(*download_tasks)
            successful_downloads.extend([path for path in batch_results if path])
            
            print(f"Batch {i//batch_size + 1}/{(len(videos_to_download)-1)//batch_size + 1} tamamlandı. "
                  f"{len([p for p in batch_results if p])} video başarıyla indirildi.")
        
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
        
        # İçeriği string'e dönüştür
        content_str = truncate_string("\n".join(content) if content else "")
        
        # API anahtarlarını kontrol et
        if not self.api_key:
            print("Uyarı: Pexels API anahtarı boş!")
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