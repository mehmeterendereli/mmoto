#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import subprocess
import shutil
import logging
from datetime import datetime
from glob import glob

class YouTubeUploader:
    """YouTube'a video yüklemek için Node.js MMotoYT uygulamasını kullanan sınıf"""
    
    def __init__(self):
        """
        YouTube yükleyici sınıfını başlatır
        """
        self.mmoto_yt_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "MMotoYT")
        self.logger = logging.getLogger("merak_makinesi")
    
    def authenticate(self):
        """
        YouTube API için kimlik doğrulama yapar - MMotoYT uygulaması otomatik yapıyor
        
        Returns:
            bool: Kimlik doğrulama başarılı ise True, değilse False
        """
        # MMotoYT klasörünün varlığını kontrol et
        if not os.path.exists(self.mmoto_yt_dir):
            self.logger.error(f"MMotoYT klasörü bulunamadı: {self.mmoto_yt_dir}")
            return False
            
        # Tokens.json dosyasının varlığını kontrol et
        tokens_path = os.path.join(self.mmoto_yt_dir, "tokens.json")
        return os.path.exists(tokens_path)
    
    def upload_video(self, video_path, title, description, tags=None, category="22", 
                    privacy_status="public", is_shorts=True, notify_subscribers=True):
        """
        YouTube'a video yükler
        
        Args:
            video_path (str): Yüklenecek video dosyasının yolu
            title (str): Video başlığı
            description (str): Video açıklaması
            tags (list): Video etiketleri
            category (str): Video kategorisi ID
            privacy_status (str): Gizlilik durumu (public, private, unlisted)
            is_shorts (bool): Shorts olarak yüklenecekse True
            notify_subscribers (bool): Abonelere bildirim gönderilecekse True
        
        Returns:
            dict: Yükleme sonucu bilgileri
        """
        if not os.path.exists(video_path):
            return {"success": False, "error": f"Video dosyası bulunamadı: {video_path}"}
        
        try:
            # MMotoYT videos dizinine video dosyasını kopyala
            videos_dir = os.path.join(self.mmoto_yt_dir, "videos")
            
            # Dizini oluştur (yoksa)
            if not os.path.exists(videos_dir):
                os.makedirs(videos_dir)
                
            # Dosya adını al
            filename = os.path.basename(video_path)
            destination = os.path.join(videos_dir, filename)
            
            # Dosyayı kopyala
            shutil.copy2(video_path, destination)
            self.logger.info(f"Video dosyası MMotoYT/videos klasörüne kopyalandı: {destination}")
            
            # JSON metadata dosyası oluştur
            if not tags:
                tags = []
                
            # Shorts için hashtag ekle
            if is_shorts and "#Shorts" not in description:
                description += "\n\n#Shorts"
                
            # Metadata oluştur
            metadata = {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": str(category),
                "privacyStatus": privacy_status
            }
            
            # Metadata dosyasını kaydet
            metadata_path = destination + ".json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Video metadata dosyası oluşturuldu: {metadata_path}")
            
            # MMotoYT dizinine geç
            os.chdir(self.mmoto_yt_dir)
            
            # MMotoYT uygulamasını çalıştır
            self.logger.info("MMotoYT uygulaması başlatılıyor...")
            print("Video MMotoYT/videos klasörüne kopyalandı. Yüklemeyi tamamlamak için:")
            print(f"1. {self.mmoto_yt_dir} klasörüne gidin")
            print("2. run.bat dosyasını çalıştırın")
            print("\nOtomatik olarak çalıştırmak için 5 saniye içinde herhangi bir tuşa basın, iptal için Ctrl+C...")
            
            # Çalışma dizinini kaydet
            current_dir = os.getcwd()
            
            try:
                # 5 saniye bekleyip kullanıcı girişi olmazsa devam et
                import msvcrt
                import sys
                import select
                
                # Windows vs Unix kontrolü
                if os.name == 'nt':  # Windows
                    import msvcrt
                    start_time = time.time()
                    print("Bekleniyor... ", end="", flush=True)
                    
                    # 5 saniye boyunca her 0.1 saniyede kontrol et
                    while time.time() - start_time < 5:
                        if msvcrt.kbhit():
                            msvcrt.getch()  # Tuşa basıldı, devam et
                            print("\nMMotoYT çalıştırılıyor...")
                            break
                        time.sleep(0.1)
                        print(".", end="", flush=True)
                    else:
                        # Süre doldu, kullanıcı araya girmedi
                        print("\nOtomatik başlatma iptal edildi.")
                        return {"success": False, "error": "Kullanıcı eylemi gerekiyor. Lütfen manuel olarak run.bat'ı çalıştırın."}
                else:  # Unix
                    print("Otomatik çalıştırma yalnızca Windows'ta desteklenir.")
                    return {"success": False, "error": "Kullanıcı eylemi gerekiyor. Lütfen manuel olarak videoyu yükleyin."}
                
                # Node.js uygulamasını çalıştır
                result = subprocess.run(
                    ["node", "index.js"],
                    capture_output=True, 
                    text=True,
                    timeout=1800  # 30 dakika timeout
                )
                
                if result.returncode == 0:
                    # Başarılı çıkış
                    output = result.stdout
                    
                    # Video ID ve URL'yi çıktıdan çıkar
                    video_id = None
                    video_url = None
                    
                    for line in output.split("\n"):
                        if "Video ID:" in line:
                            video_id = line.split("Video ID:")[1].strip()
                        elif "Video URL:" in line:
                            video_url = line.split("Video URL:")[1].strip()
                    
                    if video_id:
                        self.logger.info(f"Video başarıyla yüklendi: {video_url}")
                        
                        # Sonucu döndür
                        return {
                            "success": True,
                            "video_id": video_id,
                            "video_url": video_url,
                            "shorts_url": f"https://youtube.com/shorts/{video_id}" if is_shorts else None
                        }
                    else:
                        # Video ID bulunamadıysa, manuel yükleme talimatlarını göster
                        message = "Video kopyalandı, ancak ID bulunamadı. Lütfen MMotoYT klasöründe run.bat'i çalıştırın."
                        self.logger.info(message)
                        return {"success": True, "message": message, "video_id": None, "video_url": None}
                else:
                    # MMotoYT hatası
                    self.logger.error(f"MMotoYT hatası: {result.stderr}")
                    return {"success": False, "error": result.stderr}
                
            except subprocess.TimeoutExpired:
                self.logger.error("Video yükleme zaman aşımına uğradı (30 dakika).")
                return {"success": False, "error": "İşlem zaman aşımına uğradı (30 dakika)"}
            finally:
                # Orijinal çalışma dizinine geri dön
                os.chdir(current_dir)
            
        except Exception as e:
            self.logger.error(f"Video yükleme hatası: {str(e)}")
            return {"success": False, "error": str(e)}

# Doğrudan çalıştırma testi
if __name__ == "__main__":
    # Test kodu
    # Örneğin son oluşturulan videoyu YouTube'a yükle
    uploader = YouTubeUploader()
    
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
                        category="22",  # İnsanlar ve Bloglar
                        is_shorts=True
                    )
                    
                    if result and result.get("success", False):
                        if result.get("video_id"):
                            print(f"Video başarıyla yüklendi: {result.get('video_url', '')}")
                            if result.get('shorts_url'):
                                print(f"Shorts URL: {result.get('shorts_url', '')}")
                        else:
                            print(f"Bilgi: {result.get('message', 'Video yükleme başarılı fakat ID alınamadı')}")
                    else:
                        error_msg = result.get('error', 'Bilinmeyen hata') if result else "Yükleme sonucu alınamadı"
                        print(f"Video yükleme hatası: {error_msg}")
        else:
            print(f"Metadata dosyası bulunamadı: {metadata_path}")
    else:
        print("Hiç video bulunamadı.") 