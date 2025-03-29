#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import http.client
import httplib2
import random
import sys
import logging
from typing import Dict, Any, Optional

# Google API'ları için gerekli kütüphaneler
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
except ImportError:
    print("Google API kütüphaneleri yüklü değil. Yüklemek için:")
    print("pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

# OAuth 2.0 için gerekli izinler
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", 
          "https://www.googleapis.com/auth/youtube"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

def get_authenticated_service() -> Any:
    """
    YouTube API için kimlik doğrulama hizmeti oluşturur
    
    Returns:
        Any: Kimlik doğrulaması yapılmış YouTube servis nesnesi
    """
    credentials = None
    
    # token.json varsa yüklenir, yoksa yeni oluşturulur
    if os.path.exists("token.json"):
        credentials = Credentials.from_authorized_user_info(
            json.loads(open("token.json", "r").read()), SCOPES)
    
    # Kimlik bilgileri geçerli değilse yenilenir
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            # Kullanıcıdan kimlik doğrulama ister
            if not os.path.exists("credentials.json"):
                print("Hata: credentials.json dosyası bulunamadı!")
                print("Lütfen Google Cloud Console'dan kimlik bilgilerini indirin.")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            credentials = flow.run_local_server(port=0)
        
        # Kimlik bilgilerini kaydet
        with open("token.json", "w") as token:
            token.write(credentials.to_json())
    
    try:
        # YouTube API servisini oluştur
        return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    except HttpError as e:
        print(f"API servisi oluşturma hatası: {e}")
        return None

def upload_video(video_path: str, title: str, description: str, 
                tags: list, category_id: str = "22", privacy_status: str = "private") -> Optional[str]:
    """
    Belirtilen videoyu YouTube'a yükler
    
    Args:
        video_path (str): Yüklenecek video dosyasının yolu
        title (str): Video başlığı
        description (str): Video açıklaması
        tags (list): Video etiketleri
        category_id (str): Video kategori ID'si (22 = People & Blogs)
        privacy_status (str): Gizlilik durumu (public, unlisted, private)
    
    Returns:
        Optional[str]: Yüklenen videonun ID'si veya hata durumunda None
    """
    try:
        if not os.path.exists(video_path):
            print(f"Hata: Video dosyası bulunamadı: {video_path}")
            return None
        
        youtube = get_authenticated_service()
        if not youtube:
            return None
        
        # Video detayları
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False
            }
        }
        
        # Yükleme isteği
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        insert_request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )
        
        # Yükleme ilerlemesini takip et
        response = None
        retries = 0
        MAX_RETRIES = 10
        
        while response is None and retries < MAX_RETRIES:
            try:
                print("Yükleniyor...")
                status, response = insert_request.next_chunk()
                if status:
                    print(f"Yükleme durumu: {int(status.progress() * 100)}%")
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    retries += 1
                    if retries > MAX_RETRIES:
                        print(f"Maksimum yeniden deneme sayısına ulaşıldı: {e}")
                        break
                    time.sleep(2 ** retries)  # Exponential backoff
                else:
                    print(f"Yükleme hatası: {e}")
                    break
        
        if response:
            print(f"Video yüklendi! Video ID: {response['id']}")
            return response['id']
        else:
            print("Video yüklenemedi!")
            return None
            
    except HttpError as e:
        print(f"HttpError: {e}")
        return None
    except Exception as e:
        print(f"Beklenmeyen hata: {e}")
        return None

def upload_project_video(project_folder: str) -> Optional[str]:
    """
    Belirtilen proje klasöründeki final videoyu YouTube'a yükler
    
    Args:
        project_folder (str): Proje klasörünün yolu
    
    Returns:
        Optional[str]: Yüklenen videonun ID'si veya hata durumunda None
    """
    try:
        # Metadata dosyası kontrol edilir
        metadata_path = os.path.join(project_folder, "metadata.json")
        if not os.path.exists(metadata_path):
            print(f"Hata: Metadata dosyası bulunamadı: {metadata_path}")
            return None
        
        # Metadata okunur
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        # Final video kontrol edilir
        video_path = os.path.join(project_folder, "final_video.mp4")
        if not os.path.exists(video_path):
            print(f"Hata: Final video bulunamadı: {video_path}")
            return None
        
        # Video başlığı oluştur
        title = f"Merak Makinesi: {metadata.get('topic', 'Bilinmeyen Konu')}"
        
        # Video açıklaması oluştur
        description = (
            f"Bu video yapay zeka tarafından {metadata.get('created_at', 'bilinmeyen tarihte')} oluşturulmuştur.\n\n"
            f"Konu: {metadata.get('topic', 'Bilinmeyen')}\n"
            f"#Merak #BilgiVideosu #YapayZeka"
        )
        
        # Etiketler oluştur
        tags = metadata.get("keywords", []) + ["merak makinesi", "yapay zeka", "bilgi", "öğrenme"]
        
        # YouTube'a yükle
        return upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy_status="private"  # İlk başta private olarak yükle
        )
        
    except Exception as e:
        print(f"Proje video yükleme hatası: {str(e)}")
        return None 