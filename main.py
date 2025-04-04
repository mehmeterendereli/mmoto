#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import logging
import asyncio
from datetime import datetime
import sys
import signal
import atexit
import time

# Import modules
from modules.project_initializer import create_project_folder
from modules.content_generator import generate_content
from modules.keyword_extractor import extract_keywords
from modules.video_fetcher import fetch_videos
from modules.video_processor import process_videos
from modules.tts_generator import generate_tts
from modules.subtitle_renderer import render_subtitles
from modules.audio_merger import merge_audio
from modules.closing_scene_adder import add_closing_scene
from modules.metadata_writer import write_metadata
from modules.youtube_uploader import YouTubeUploader
from modules.topic_generator import generate_topic, generate_english_topic, generate_topic_international  # İki fonksiyonu da import edelim

# Force exit after a certain delay - use as a safety net
def force_exit():
    print("\nForcing program exit...")
    # Force exit with os._exit which is more aggressive than sys.exit
    time.sleep(1)
    os._exit(0)

# Register the force exit function to run at program exit
atexit.register(force_exit)

def load_config():
    """Loads the configuration file"""
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

async def process_single_video(topic, openai_api_key="", pexels_api_key="", pixabay_api_key="", youtube_api_key="", 
                              language="tr", tts_language="tr", subtitle_language="tr", max_videos=None, 
                              continuous_mode=False, log_callback=None):
    """
    Tek bir video işleme süreci için asenkron fonksiyon
    
    Args:
        topic (str): Video konusu
        openai_api_key (str): OpenAI API anahtarı
        pexels_api_key (str): Pexels API anahtarı
        pixabay_api_key (str): Pixabay API anahtarı
        youtube_api_key (str): YouTube API anahtarı
        language (str): İçerik dili (tr, en vb.)
        tts_language (str): Seslendirme dili (tr, en vb.)
        subtitle_language (str): Altyazı dili (tr, en vb.)
        max_videos (int): Maksimum video sayısı
        continuous_mode (bool): Sürekli çalışma modu
        log_callback (callable): Log mesajlarını göndermek için callback fonksiyonu
        
    Returns:
        tuple: (success, video_url) - İşlem başarılı mı ve video URL'si
    """
    def log_message(message, is_error=False):
        logging.info(message) if not is_error else logging.error(message)
        if log_callback:
            log_callback(message, is_error)
    
    log_message(f"'{topic}' konusu için video üretimi başlatılıyor... [Dil: {language}]")
    
    # Güncel dil ayarlarını kaydet - Gerçek seçilen dilleri göster, varsayılan değil
    log_message(f"Kullanılan içerik dili: {language}")
    log_message(f"Kullanılan seslendirme dili: {tts_language}")
    log_message(f"Kullanılan altyazı dili: {subtitle_language}")
    
    final_video_path = None
    video_url = None
    success = False
    
    try:
        # 1. CONFIG LOADING - ADIM 1: Yapılandırma Yükleme
        config = {}
        if not all([openai_api_key, pexels_api_key]):
            config = load_config()
            openai_api_key = openai_api_key or config.get("openai_api_key", "")
            pexels_api_key = pexels_api_key or config.get("pexels_api_key", "")
            pixabay_api_key = pixabay_api_key or config.get("pixabay_api_key", "")
            youtube_api_key = youtube_api_key or config.get("youtube_api_key", "")
        
        # 2. PROJECT INITIALIZATION - ADIM 2: Proje Klasörü Oluşturma
        project_folder = create_project_folder()
        log_message(f"Project folder created: {project_folder}")
        
        # 3. CONTENT GENERATION - ADIM 3: İçerik Oluşturma (İçerik dili kullanılır)
        try:
            content_data = generate_content(topic, language=language)
            log_message(f"{language} dilinde içerik oluşturuldu")
            
            # İçerik metinlerini dosyalara kaydet
            for i, sentence in enumerate(content_data["response"]):
                with open(os.path.join(project_folder, f"text_{i+1:02d}.txt"), "w", encoding="utf-8") as f:
                    f.write(sentence)
            log_message("Content saved to text files")
        except Exception as e:
            log_message(f"İçerik oluşturma hatası: {str(e)}", True)
            return False, None
        
        # 4. KEYWORD EXTRACTION - ADIM 4: Anahtar Kelime Çıkarma
        try:
            keywords = extract_keywords(content_data["response"], topic, language=language, openai_api_key=openai_api_key)
            log_message(f"Keywords: {keywords}")
            
            # Anahtar kelimeleri bir dosyaya kaydet (video işleme için kullanılacak)
            with open(os.path.join(project_folder, "pexels_keywords.txt"), "w", encoding="utf-8") as f:
                for keyword in keywords:
                    f.write(f"{keyword}\n")
        except Exception as e:
            log_message(f"Anahtar kelime çıkarma hatası: {str(e)}", True)
            keywords = [topic]  # En azından konu başlığını kullan
        
        # 5. VIDEO FETCH - ADIM 5: Video İndirme
        try:
            videos = await fetch_videos(
                keywords,
                pexels_api_key,
                openai_api_key,
                topic,
                content_data["response"],
                project_folder,
                min_score=3.0,
                language=language  # Çeviriler için kullanılır, arama her zaman İngilizce
            )
            log_message(f"{len(videos)} videos downloaded")
            
            # Video yoksa veya indirilemezse, işleme devam etme
            if not videos:
                log_message("Hiç video indirilemedi veya bulunamadı.", True)
                # İşleme devam edebiliriz ama boş bir video ile
            
        except Exception as e:
            log_message(f"Video indirme hatası: {str(e)}", True)
            videos = []  # Boş liste ile devam et
        
        # 6. VIDEO PROCESSING - ADIM 6: Video İşleme
        try:
            video_resolution = config.get("video_resolution", "1080x1920") if config else "1080x1920"
            # Çözünürlük string ise, tuple'a çevir
            if isinstance(video_resolution, str) and "x" in video_resolution:
                width, height = map(int, video_resolution.split("x"))
                resolution_tuple = (width, height)
            else:
                resolution_tuple = (1080, 1920)  # Varsayılan çözünürlük
                
            processed_video = process_videos(videos, resolution_tuple, project_folder)
            log_message("Videos processed")
            
            # İşlenmiş video yolunu kontrol et
            if not os.path.exists(processed_video):
                log_message(f"İşlenmiş video dosyası bulunamadı: {processed_video}", True)
                # İşlem devam edebilir, ses dosyaları oluşturulabilir
            
        except Exception as e:
            log_message(f"Video işleme hatası: {str(e)}", True)
            processed_video = os.path.join(project_folder, "processed_video.mp4")
            # Video işleme başarısız olsa bile, ses oluşturmaya devam edebiliriz
        
        # 7. TTS GENERATION - ADIM 7: TTS (Text-to-Speech) Oluşturma
        try:
            default_tts_voice = config.get("default_tts_voice", "alloy") if config else "alloy"
            audio_files = generate_tts(
                content_data["response"],
                openai_api_key,
                default_tts_voice,
                project_folder,
                language=tts_language  # TTS dili kullanılır
            )
            log_message(f"{len(audio_files)} audio files created")
            
            # Ses dosyası yoksa, işleme devam etme
            if not audio_files:
                log_message("Ses dosyaları oluşturulamadı.", True)
                # İşlem devam edebilir ama altyazı ile
            
        except Exception as e:
            log_message(f"TTS oluşturma hatası: {str(e)}", True)
            audio_files = []  # Boş liste ile devam et
        
        # 8. AUDIO MERGING - ADIM 8: Ses Birleştirme
        try:
            if audio_files:
                video_with_audio = merge_audio(processed_video, audio_files, project_folder)
                log_message("Audio merged")
            else:
                video_with_audio = processed_video  # Ses yoksa orijinal video ile devam et
                log_message("Ses dosyası olmadığı için seslendirme atlandı", True)
        except Exception as e:
            log_message(f"Ses birleştirme hatası: {str(e)}", True)
            video_with_audio = processed_video  # Orijinal video ile devam et
        
        # 9. SUBTITLE RENDERING - ADIM 9: Altyazı Oluşturma
        try:
            font_path = config.get("font_path", "") if config else ""
            subtitled_video = render_subtitles(
                video_with_audio,
                content_data["response"],
                font_path,
                project_folder,
                subtitle_language=subtitle_language,  # Altyazı dili kullanılır
                content_language=language,           # İçerik dili gerekirse çeviri için kullanılır
                openai_api_key=openai_api_key
            )
            log_message(f"Subtitles added in {subtitle_language} language")
        except Exception as e:
            log_message(f"Altyazı oluşturma hatası: {str(e)}", True)
            subtitled_video = video_with_audio  # Altyazısız video ile devam et
        
        # 10. CLOSING SCENE - ADIM 10: Kapanış Sahnesi Ekleme
        try:
            closing_video_path = config.get("closing_video_path", "") if config else ""
            final_video = add_closing_scene(subtitled_video, closing_video_path, project_folder)
            log_message("Closing scene added")
            final_video_path = final_video  # Son video yolunu kaydet
        except Exception as e:
            log_message(f"Kapanış sahnesi ekleme hatası: {str(e)}", True)
            final_video_path = subtitled_video  # Kapanış sahnesi olmadan devam et
        
        # 11. METADATA CREATION - ADIM 11: Metadata Oluşturma
        try:
            metadata = write_metadata(
                project_folder, 
                topic, 
                keywords, 
                "gpt-4o", 
                default_tts_voice, 
                language=language,
                tts_language=tts_language,
                subtitle_language=subtitle_language
            )
            log_message(f"Metadata created with title: {metadata.get('title', 'No title')}")
        except Exception as e:
            log_message(f"Metadata oluşturma hatası: {str(e)}", True)
            metadata = {
                "topic": topic,
                "title": f"Facts About {topic}",
                "keywords": keywords,
                "language": language,
                "tts_language": tts_language,
                "subtitle_language": subtitle_language
            }
        
        log_message(f"Process completed! Final video: {final_video_path}")
        
        # 12. VIDEO UPLOAD - ADIM 12: YouTube'a Yükleme (İsteğe bağlı)
        if youtube_api_key:
            log_message("Starting automatic YouTube upload...")
            try:
                # Metadata kontrolü ve eksik verileri tamamlama
                metadata_path = os.path.join(project_folder, "metadata.json")
                if not os.path.exists(metadata_path):
                    log_message("Metadata file not found, creating backup metadata")
                    backup_metadata = {
                        "topic": topic,
                        "title": f"Facts About {topic}",
                        "content": "\n".join(content_data["response"]) + "\n\n#Shorts #Educational",
                        "keywords": keywords + ["educational", "shorts", "facts"],
                        "category_id": "27",  # Education
                        "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "language": language,
                        "tts_language": tts_language,
                        "subtitle_language": subtitle_language
                    }
                    with open(metadata_path, "w", encoding="utf-8") as f:
                        json.dump(backup_metadata, f, ensure_ascii=False, indent=4)
                    metadata = backup_metadata
                    log_message("Backup metadata created successfully")
                else:
                    # Metadata dosyası varsa oku
                    try:
                        with open(metadata_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                    except Exception as e:
                        log_message(f"Error reading metadata file: {str(e)}, using backup metadata", True)
                        metadata = {
                            "topic": topic,
                            "title": f"Facts About {topic}",
                            "content": "\n".join(content_data["response"]) + "\n\n#Shorts #Educational",
                            "keywords": keywords + ["educational", "shorts", "facts"],
                            "category_id": "27",  # Education
                            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "language": language,
                            "tts_language": tts_language,
                            "subtitle_language": subtitle_language
                        }
                
                # Başlık ve açıklama uzunluğunu kontrol et
                title = metadata.get("title", f"Facts About {topic}")
                if len(title) > 100:
                    title = title[:97] + "..."
                    
                description = metadata.get("content", "")
                if not description and content_data and "response" in content_data:
                    description = "\n".join(content_data["response"]) + "\n\n#Shorts #Educational"
                    
                if len(description) > 5000:
                    description = description[:4997] + "..."
                
                # Video etiketlerini hazırla
                tags = [str(tag) for tag in metadata.get("keywords", [])]
                if "Shorts" not in tags and "shorts" not in tags:
                    tags.append("Shorts")
                
                # Etiket yoksa varsayılanları kullan
                if not tags:
                    tags = ["educational", "shorts", "facts", topic.lower()]
                    
                # Kategori ID'sini al
                category_id = metadata.get("category_id", "27")  # Varsayılan Education
                
                # Video dosyasını kontrol et
                if not os.path.exists(final_video_path):
                    log_message(f"Final video not found at path: {final_video_path}", True)
                    # Proje klasöründe herhangi bir mp4 dosyası ara
                    mp4_files = [f for f in os.listdir(project_folder) if f.endswith('.mp4')]
                    if mp4_files:
                        final_video_path = os.path.join(project_folder, mp4_files[0])
                        log_message(f"Using alternative video file: {final_video_path}")
                    else:
                        raise FileNotFoundError(f"No video files found in {project_folder}")
                
                # YouTube yükleyiciyi başlat
                uploader = YouTubeUploader()
                
                # Yükleme bilgilerini göster
                log_message(f"Uploading video with title: {title}")
                log_message(f"Category: {category_id}")
                log_message(f"Tags: {', '.join(tags[:5])}{'...' if len(tags) > 5 else ''}")
                
                # Videoyu yükle
                result = uploader.upload_video(
                    video_path=final_video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    category=category_id,
                    privacy_status="public",
                    is_shorts=True
                )
                
                if result and result.get("success", False):
                    if result.get("video_id"):
                        video_url = result.get('video_url', '')
                        log_message(f"Video successfully uploaded to YouTube: {video_url}")
                        success = True
                    else:
                        log_message("Upload successful but video ID not returned", True)
                else:
                    error_msg = result.get("error", "Unknown error") if result else "No result returned"
                    log_message(f"Upload failed: {error_msg}", True)
                    
            except Exception as e:
                log_message(f"Error during upload: {str(e)}", True)
        else:
            # YouTube API anahtarı yoksa yükleme yapmadan işlemi tamamla
            success = True
            log_message("YouTube API key not provided, skipping upload.")
        
        # Son bir kontrol - herhangi bir video oluşturulduysa başarılı say
        if os.path.exists(final_video_path) and os.path.getsize(final_video_path) > 0:
            success = True
        else:
            log_message("Final video not found or empty", True)
            success = False
        
        log_message(f"İşlem {'tamamlandı' if success else 'başarısız oldu'}")
        return success, video_url
        
    except Exception as e:
        log_message(f"An error occurred: {str(e)}", True)
        return False, None

async def async_main(continuous_mode=False, max_videos=None, language='tr', tts_language='tr', subtitle_language='tr'):
    """Ana asenkron fonksiyon, sürekli mod desteği ile"""
    # Logging settings
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('merak_makinesi')
    
    try:
        # Load config file
        config = load_config()
        
        # Video sayacı
        video_count = 0
        
        # Sürekli mod
        while True:
            try:
                # Maksimum video sayısını kontrol et
                if max_videos is not None and video_count >= max_videos:
                    logger.info(f"Maksimum video sayısına ulaşıldı ({max_videos}). Program sonlandırılıyor.")
                    break
                
                # Konu seçimi (manuel veya otomatik)
                if continuous_mode:
                    # Otomatik olarak GPT ile yeni konu üret (dil seçeneğine göre)
                    if language == 'en':
                        topic = generate_english_topic(config["openai_api_key"])
                        logger.info(f"New topic generated with GPT: {topic}")
                    elif language in ['es', 'fr', 'de', 'it', 'pt', 'ru', 'ar']:
                        # Farklı diller için uluslararası konu üreteci
                        topic = generate_topic_international(config["openai_api_key"], language)
                        logger.info(f"New topic generated with GPT ({language}): {topic}")
                    else:
                        topic = generate_topic(config["openai_api_key"])
                        logger.info(f"GPT ile yeni konu üretildi: {topic}")
                    
                    # Bir sonraki videoya geçmeden önce kısa bir bekleme süresi
                    print(f"\n{'='*50}")
                    print(f"{'Next topic' if language == 'en' else 'Sıradaki konu'}: {topic}")
                    print(f"{'='*50}\n")
                    time.sleep(3)  # 3 saniye bekle
                else:
                    # Manuel konu girişi
                    topic = input("Please enter a topic (or 'q' to exit): " if language == 'en' else "Lütfen bir konu girin (çıkış için 'q'): ")
                    if topic.lower() == 'q':
                        break
                
                # Video işleme - doğru dil parametrelerini kullanarak
                success, video_url = await process_single_video(
                    topic, 
                    config["openai_api_key"], 
                    config["pexels_api_key"], 
                    config["pixabay_api_key"], 
                    config["youtube_api_key"], 
                    language,  # İçerik dili
                    tts_language,  # Seslendirme dili
                    subtitle_language,  # Altyazı dili
                    max_videos, 
                    continuous_mode
                )
                
                # Video sayacını artır
                if success:
                    video_count += 1
                    logger.info(f"Video {video_count} tamamlandı. URL: {video_url}")
                
                # Sürekli modda değilse döngüyü sonlandır
                if not continuous_mode:
                    break
                
                # Sürekli modda sonraki video için bekle
                logger.info(f"Sonraki video için bekleniyor... (20 saniye)")
                time.sleep(20)  # API rate limitlerini aşmamak için bekle
                
            except KeyboardInterrupt:
                logger.info("Kullanıcı tarafından işlem kesildi.")
                break
            except Exception as e:
                logger.error(f"Video işleme hatası: {str(e)}", exc_info=True)
                # Hata durumunda tekrar başlamadan önce biraz bekle
                time.sleep(10)
                # Hataya rağmen döngüye devam et
                continue
        
        # İşlem sonlandırma mesajı
        logger.info("Program execution completed successfully, exiting...")
        print("\nProgram başarıyla tamamlandı!")
        
        return 0  # Return success code
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return 1  # Return error code
    
    finally:
        # Make sure to close all pending tasks
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        if tasks:
            logger.info(f"Cancelling {len(tasks)} pending tasks...")
            for task in tasks:
                task.cancel()
            
            # Allow tasks to cancel properly
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info("All pending tasks cancelled")
            except Exception as e:
                logger.warning(f"Error cancelling tasks: {str(e)}")

def main():
    """Main function called normally, manages async operations"""
    # Handle Ctrl+C gracefully
    if os.name == 'nt':  # Windows
        signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))
    else:  # Unix
        signal.signal(signal.SIGINT, lambda x, y: sys.exit(0))
        signal.signal(signal.SIGTERM, lambda x, y: sys.exit(0))
    
    try:
        # Komut satırı parametrelerini kontrol et
        continuous_mode = "--continuous" in sys.argv or "-c" in sys.argv
        max_videos = None
        
        # Varsayılan dil ayarları
        language = 'tr'  # İçerik dili
        tts_language = 'tr'  # TTS dili
        subtitle_language = 'tr'  # Altyazı dili
        
        # Maksimum video sayısını kontrol et
        for arg in sys.argv:
            if arg.startswith("--max="):
                try:
                    max_videos = int(arg.split("=")[1])
                except:
                    pass
            # İçerik dili parametresi
            elif arg.startswith("--lang=") or arg.startswith("-l="):
                lang = arg.split("=")[1].lower()
                if lang in ['en', 'tr', 'es', 'fr', 'de']:
                    language = lang
            # TTS dili parametresi      
            elif arg.startswith("--tts="):
                tts_lang = arg.split("=")[1].lower()
                if tts_lang in ['en', 'tr', 'es', 'fr', 'de']:
                    tts_language = tts_lang
            # Altyazı dili parametresi
            elif arg.startswith("--subtitle=") or arg.startswith("--sub="):
                sub_lang = arg.split("=")[1].lower()
                if sub_lang in ['en', 'tr', 'es', 'fr', 'de']:
                    subtitle_language = sub_lang
        
        # Eğer sürekli çalışma modu seçildiyse kullanıcıyı bilgilendir
        if continuous_mode:
            print(f"\n{'='*50}")
            print("Continuous mode activated!" if language == 'en' else "Sürekli çalışma modu etkinleştirildi!")
            if max_videos:
                print(f"{'Maximum' if language == 'en' else 'Maksimum'} {max_videos} {'videos will be produced' if language == 'en' else 'video üretilecek'}")
            
            print("Content Language / İçerik Dili: " + language)
            print("TTS Language / Seslendirme Dili: " + tts_language)
            print("Subtitle Language / Altyazı Dili: " + subtitle_language)
            
            print("The program will automatically create and upload videos" if language == 'en' else "Program, GPT tarafından üretilen konulara göre otomatik olarak")
            print("based on topics generated by GPT." if language == 'en' else "video oluşturup YouTube'a yükleyecek.")
            print("Press Ctrl+C to stop." if language == 'en' else "Durdurmak için Ctrl+C tuşlarına basın.")
            print(f"{'='*50}\n")
            time.sleep(2)
        
        # Set a reasonable timeout for the event loop
        exit_code = asyncio.run(async_main(
            continuous_mode=continuous_mode, 
            max_videos=max_videos, 
            language=language, 
            tts_language=tts_language, 
            subtitle_language=subtitle_language
        ), debug=False)
        
        # Add a short delay to allow for any pending operations to complete
        print("İşlemler tamamlanıyor ve çıkılıyor...")
        time.sleep(2)
        
        sys.exit(exit_code)  # Explicitly exit with code
    except KeyboardInterrupt:
        print("\nProgram interrupted by user, exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Unhandled exception: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    import threading
    main()
