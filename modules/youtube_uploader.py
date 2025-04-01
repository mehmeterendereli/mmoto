#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import http.client
import httplib2
import random
import logging
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# YouTube API için gerekli izinler
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 
          'https://www.googleapis.com/auth/youtube']

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# YouTube kategorileri
YOUTUBE_CATEGORIES = {
    "film_animation": 1,
    "autos_vehicles": 2,
    "music": 10,
    "pets_animals": 15,
    "sports": 17,
    "travel_events": 19,
    "gaming": 20,
    "people_blogs": 22,
    "comedy": 23,
    "entertainment": 24,
    "news_politics": 25,
    "howto_style": 26,
    "education": 27,
    "science_technology": 28
}

class YouTubeUploader:
    """YouTube'a video yüklemek için kullanılan sınıf"""
    
    def __init__(self, client_secrets_file="client_secret.json", credentials_file="youtube_token.json"):
        """
        YouTube yükleyici sınıfını başlatır
        
        Args:
            client_secrets_file (str): Google API Client Secret dosyası
            credentials_file (str): Kayıtlı oturum bilgisi dosyası
        """
        self.client_secrets_file = client_secrets_file
        self.credentials_file = credentials_file
        self.youtube = None
        self.logger = logging.getLogger("merak_makinesi")
    
    def authenticate(self):
        """
        YouTube API için kimlik doğrulama yapar
        
        Returns:
            bool: Kimlik doğrulama başarılı ise True, değilse False
        """
        credentials = None
        
        # Daha önce oluşturulmuş kimlik bilgilerini kontrol et
        if os.path.exists(self.credentials_file):
            try:
                credentials = Credentials.from_authorized_user_info(
                    json.load(open(self.credentials_file)), SCOPES)
            except Exception as e:
                self.logger.error(f"Kimlik bilgileri yüklenirken hata: {str(e)}")
        
        # Kimlik bilgilerinin geçerli olup olmadığını kontrol et
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                except Exception as e:
                    self.logger.error(f"Kimlik bilgileri yenilenirken hata: {str(e)}")
                    credentials = None
            
            # Yeni kimlik bilgileri oluştur
            if not credentials:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.client_secrets_file, SCOPES)
                    credentials = flow.run_local_server(port=0)
                    
                    # Kimlik bilgilerini kaydet
                    with open(self.credentials_file, 'w') as token:
                        token.write(credentials.to_json())
                except Exception as e:
                    self.logger.error(f"Kimlik doğrulama hatası: {str(e)}")
                    return False
        
        # YouTube API servisini oluştur
        try:
            self.youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, 
                               credentials=credentials)
            return True
        except Exception as e:
            self.logger.error(f"YouTube API servisi oluşturulurken hata: {str(e)}")
            return False
    
    def upload_video(self, video_path, title, description, tags=None, category=28, 
                    privacy_status="public", is_shorts=True, notify_subscribers=True):
        """
        YouTube'a video yükler
        
        Args:
            video_path (str): Yüklenecek video dosyasının yolu
            title (str): Video başlığı
            description (str): Video açıklaması
            tags (list): Video etiketleri
            category (int): Video kategorisi 
            privacy_status (str): Gizlilik durumu (public, private, unlisted)
            is_shorts (bool): Shorts olarak yüklenecekse True
            notify_subscribers (bool): Abonelere bildirim gönderilecekse True
        
        Returns:
            dict: Yükleme sonucu bilgileri
        """
        if not self.youtube:
            if not self.authenticate():
                return {"success": False, "error": "Kimlik doğrulama başarısız"}
        
        if not os.path.exists(video_path):
            return {"success": False, "error": f"Video dosyası bulunamadı: {video_path}"}
        
        if not tags:
            tags = []
        
        # İlk etikete dönüştür (YouTube API gereksinimleri)
        if isinstance(tags, list):
            tags = [tag.strip() for tag in tags if tag.strip()]
        
        # Kategori ID'yi doğrula
        if isinstance(category, str) and category in YOUTUBE_CATEGORIES:
            category = YOUTUBE_CATEGORIES[category]
        
        # Shorts için hashtag ekle
        if is_shorts and "#Shorts" not in description:
            description += "\n\n#Shorts"
        
        try:
            # Video meta verilerini hazırla
            video_metadata = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": str(category)
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False,
                    "notifySubscribers": notify_subscribers
                }
            }
            
            # MediaFileUpload nesnesi oluştur
            media = MediaFileUpload(video_path, 
                                  chunksize=1024*1024, 
                                  resumable=True)
            
            # Yükleme isteği oluştur
            insert_request = self.youtube.videos().insert(
                part=",".join(video_metadata.keys()),
                body=video_metadata,
                media_body=media
            )
            
            self.logger.info(f"Video yükleniyor: {title}")
            
            # Yükleme işlemini başlat ve ilerleyişi izle
            response = None
            while response is None:
                status, response = insert_request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    self.logger.info(f"Yükleme ilerlemesi: {progress}%")
            
            # Başarılı yükleme sonrası video bilgilerini al
            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            shorts_url = f"https://youtube.com/shorts/{video_id}"
            
            self.logger.info(f"Video başarıyla yüklendi: {video_url}")
            
            # Sonucu döndür
            return {
                "success": True,
                "video_id": video_id,
                "video_url": video_url,
                "shorts_url": shorts_url if is_shorts else None
            }
            
        except HttpError as e:
            error_content = json.loads(e.content.decode())
            error_message = error_content.get('error', {}).get('message', str(e))
            self.logger.error(f"YouTube API hatası: {error_message}")
            return {"success": False, "error": error_message}
            
        except Exception as e:
            self.logger.error(f"Video yükleme hatası: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def update_video_metadata(self, video_id, title=None, description=None, tags=None, 
                             category=None, privacy_status=None):
        """
        Yüklenmiş videonun meta verilerini günceller
        
        Args:
            video_id (str): Güncellenecek video ID'si
            title (str): Yeni başlık
            description (str): Yeni açıklama
            tags (list): Yeni etiketler
            category (int): Yeni kategori
            privacy_status (str): Yeni gizlilik durumu
        
        Returns:
            dict: Güncelleme sonucu bilgileri
        """
        if not self.youtube:
            if not self.authenticate():
                return {"success": False, "error": "Kimlik doğrulama başarısız"}
        
        try:
            # Mevcut video meta verilerini al
            video_response = self.youtube.videos().list(
                part="snippet,status",
                id=video_id
            ).execute()
            
            if not video_response.get("items"):
                return {"success": False, "error": f"Video bulunamadı: {video_id}"}
            
            # Mevcut meta verileri al
            video_snippet = video_response["items"][0]["snippet"]
            video_status = video_response["items"][0]["status"]
            
            # Yeni meta verileri hazırla
            body = {
                "id": video_id,
                "snippet": {
                    "title": title if title is not None else video_snippet["title"],
                    "description": description if description is not None else video_snippet["description"],
                    "tags": tags if tags is not None else video_snippet.get("tags", []),
                    "categoryId": str(category) if category is not None else video_snippet["categoryId"]
                },
                "status": {
                    "privacyStatus": privacy_status if privacy_status is not None else video_status["privacyStatus"]
                }
            }
            
            # Güncelleme isteği gönder
            update_response = self.youtube.videos().update(
                part="snippet,status",
                body=body
            ).execute()
            
            self.logger.info(f"Video meta verileri güncellendi: {video_id}")
            
            return {
                "success": True,
                "video_id": video_id,
                "video_url": f"https://www.youtube.com/watch?v={video_id}"
            }
            
        except HttpError as e:
            error_content = json.loads(e.content.decode())
            error_message = error_content.get('error', {}).get('message', str(e))
            self.logger.error(f"YouTube API hatası: {error_message}")
            return {"success": False, "error": error_message}
            
        except Exception as e:
            self.logger.error(f"Meta veri güncelleme hatası: {str(e)}")
            return {"success": False, "error": str(e)}

# Doğrudan çalıştırma testi
if __name__ == "__main__":
    # Test kodu
    # Örneğin son oluşturulan videoyu YouTube'a yükle
    uploader = YouTubeUploader()
    
    from glob import glob
    import os
    
    # Son oluşturulan video klasörünü bul
    output_dirs = sorted(glob("output/video_*"), key=os.path.getmtime)
    
    if output_dirs:
        last_output_dir = output_dirs[-1]
        video_path = os.path.join(last_output_dir, "final_video.mp4")
        
        # Metadata dosyasını oku
        metadata_path = os.path.join(last_output_dir, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # YouTube'a yükle
            if os.path.exists(video_path):
                print(f"Son oluşturulan video: {video_path}")
                print(f"Başlık: {metadata.get('title', 'Başlıksız Video')}")
                
                # Kullanıcıya sor
                response = input("Bu videoyu YouTube'a yüklemek istiyor musunuz? (e/h): ")
                
                if response.lower() in ["e", "evet", "y", "yes"]:
                    result = uploader.upload_video(
                        video_path=video_path,
                        title=metadata.get("title", "Otomatik Oluşturulmuş Video"),
                        description=metadata.get("content", ""),
                        tags=metadata.get("keywords", []) + ["Shorts", "kısavideo"],
                        category="education",
                        is_shorts=True
                    )
                    
                    if result["success"]:
                        print(f"Video başarıyla yüklendi: {result['video_url']}")
                        print(f"Shorts URL: {result['shorts_url']}")
                    else:
                        print(f"Video yükleme hatası: {result['error']}")
        else:
            print(f"Metadata dosyası bulunamadı: {metadata_path}")
    else:
        print("Hiç video bulunamadı.") 