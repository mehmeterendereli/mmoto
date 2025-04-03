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
from modules.topic_generator import generate_topic, generate_english_topic  # İki fonksiyonu da import edelim

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

async def process_single_video(topic):
    """Tek bir video işleme süreci için asenkron fonksiyon"""
    logging.info(f"'{topic}' konusu için video üretimi başlatılıyor...")
    
    try:
        # Load config file
        config = load_config()
        
        # Create new project folder
        project_folder = create_project_folder()
        logging.info(f"Project folder created: {project_folder}")
        
        # Generate content
        content_data = generate_content(topic)
        logging.info("Content generated")
        
        # Save content sentences to text files for metadata generation
        for i, sentence in enumerate(content_data["response"]):
            with open(os.path.join(project_folder, f"text_{i+1:02d}.txt"), "w", encoding="utf-8") as f:
                f.write(sentence)
        logging.info("Content saved to text files")
        
        # Extract keywords
        keywords = extract_keywords(content_data["response"], topic)
        logging.info(f"Keywords: {keywords}")
        
        # Use new async video fetching function
        videos = await fetch_videos(
            keywords, 
            config["pexels_api_key"], 
            config["openai_api_key"], 
            topic, 
            content_data["response"], 
            project_folder, 
            min_score=3.0
        )
        logging.info(f"{len(videos)} videos downloaded")
        
        # Process videos
        processed_video = process_videos(videos, config["video_resolution"], project_folder)
        logging.info("Videos processed")
        
        # Generate TTS
        audio_files = generate_tts(content_data["response"], config["openai_api_key"],
                               config["default_tts_voice"], project_folder)
        logging.info(f"{len(audio_files)} audio files created")
        
        # Merge audio first, before subtitles
        video_with_audio = merge_audio(processed_video, audio_files, project_folder)
        logging.info("Audio merged")
        
        # NOW add subtitles to the audio-synced video
        subtitled_video = render_subtitles(video_with_audio, content_data["response"], 
                                      config["font_path"], project_folder)
        logging.info("Subtitles added")
        
        # Add closing scene
        final_video = add_closing_scene(subtitled_video, config["closing_video_path"], project_folder)
        logging.info("Closing scene added")
        
        # Create metadata
        metadata = write_metadata(project_folder, topic, keywords, "gpt-4o", config["default_tts_voice"])
        logging.info(f"Metadata created with title: {metadata.get('title', 'No title')}")
        
        logging.info(f"Process completed! Final video: {final_video}")
        
        # Auto-upload video to YouTube with optimized metadata
        logging.info("Starting automatic YouTube upload...")
        try:
            # Check if metadata file exists, create if not
            metadata_path = os.path.join(project_folder, "metadata.json")
            if not os.path.exists(metadata_path):
                logging.warning("Metadata file not found, creating backup metadata")
                backup_metadata = {
                    "topic": topic,
                    "title": f"Facts About {topic}",
                    "content": "\n".join(content_data["response"]) + "\n\n#Shorts #Educational",
                    "keywords": keywords + ["educational", "shorts", "facts"],
                    "category_id": "27",  # Education
                    "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(backup_metadata, f, ensure_ascii=False, indent=4)
                metadata = backup_metadata
                logging.info("Backup metadata created successfully")
            else:
                # If file exists but can't be read, try to re-read it
                try:
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                except Exception as e:
                    logging.warning(f"Error reading metadata file: {str(e)}, using backup metadata")
                    metadata = {
                        "topic": topic,
                        "title": f"Facts About {topic}",
                        "content": "\n".join(content_data["response"]) + "\n\n#Shorts #Educational",
                        "keywords": keywords + ["educational", "shorts", "facts"],
                        "category_id": "27",  # Education
                        "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
            
            # Check and limit title and description length
            title = metadata.get("title", f"Facts About {topic}")
            if len(title) > 100:
                title = title[:97] + "..."
                
            description = metadata.get("content", "")
            if not description and content_data and "response" in content_data:
                description = "\n".join(content_data["response"]) + "\n\n#Shorts #Educational"
                
            if len(description) > 5000:
                description = description[:4997] + "..."
            
            # Prepare video tags - ensuring they're all strings
            tags = [str(tag) for tag in metadata.get("keywords", [])]
            if "Shorts" not in tags and "shorts" not in tags:
                tags.append("Shorts")
            
            # Make sure we have at least some tags
            if not tags:
                tags = ["educational", "shorts", "facts", topic.lower()]
                
            # Get category ID from metadata
            category_id = metadata.get("category_id", "27")  # Default to Education if not specified
            
            # Verify final video exists
            if not os.path.exists(final_video):
                logging.error(f"Final video not found at path: {final_video}")
                # Try to find any mp4 file in the project folder
                mp4_files = [f for f in os.listdir(project_folder) if f.endswith('.mp4')]
                if mp4_files:
                    final_video = os.path.join(project_folder, mp4_files[0])
                    logging.info(f"Using alternative video file: {final_video}")
                else:
                    raise FileNotFoundError(f"No video files found in {project_folder}")
            
            # Initialize YouTube uploader
            uploader = YouTubeUploader()
            
            # Show upload information
            logging.info(f"Uploading video with title: {title}")
            logging.info(f"Category: {category_id}")
            logging.info(f"Tags: {', '.join(tags[:5])}{'...' if len(tags) > 5 else ''}")
            
            result = uploader.upload_video(
                video_path=final_video,
                title=title,
                description=description,
                tags=tags,
                category=category_id,
                privacy_status="public",
                is_shorts=True
            )
            
            if result and result.get("success", False):
                if result.get("video_id"):
                    logging.info(f"Video successfully uploaded to YouTube: {result.get('video_url', '')}")
                    print(f"Video uploaded to YouTube: {result.get('video_url', '')}")
                    
                    if result.get('shorts_url'):
                        print(f"Shorts URL: {result.get('shorts_url', '')}")
                    
                    # Add YouTube information to metadata
                    metadata["youtube_url"] = result.get("video_url", "")
                    metadata["youtube_shorts_url"] = result.get("shorts_url", "")
                    metadata["youtube_video_id"] = result.get("video_id", "")
                    
                    # Save updated metadata
                    with open(metadata_path, "w", encoding="utf-8") as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=4)
                    
                    return True, result.get("video_url", "")
                else:
                    # If no Video ID, show manual upload message
                    logging.info(f"Video copied but ID not retrieved: {result.get('message', '')}")
                    print(f"Info: {result.get('message', 'Video upload completed but ID not retrieved')}")
                    return True, None
            else:
                error_msg = result.get('error', 'Unknown error') if result else "Upload result not received"
                logging.error(f"YouTube upload error: {error_msg}")
                print(f"YouTube upload error: {error_msg}")
                return False, None
                
        except Exception as e:
            error_msg = f"Error during YouTube upload process: {str(e)}"
            logging.error(error_msg)
            print(error_msg)
            return False, None
        
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}", exc_info=True)
        return False, None

async def async_main(continuous_mode=False, max_videos=None, language='en'):
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
                
                # Video işleme
                success, video_url = await process_single_video(topic)
                
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
        language = 'en'  # Varsayılan dil İngilizce
        
        # Maksimum video sayısını kontrol et
        for arg in sys.argv:
            if arg.startswith("--max="):
                try:
                    max_videos = int(arg.split("=")[1])
                except:
                    pass
            elif arg.startswith("--lang=") or arg.startswith("-l="):
                lang = arg.split("=")[1].lower()
                if lang in ['en', 'tr']:
                    language = lang
        
        # Eğer sürekli çalışma modu seçildiyse kullanıcıyı bilgilendir
        if continuous_mode:
            print(f"\n{'='*50}")
            print("Continuous mode activated!" if language == 'en' else "Sürekli çalışma modu etkinleştirildi!")
            if max_videos:
                print(f"{'Maximum' if language == 'en' else 'Maksimum'} {max_videos} {'videos will be produced' if language == 'en' else 'video üretilecek'}")
            print("Language / Dil: " + ("English 🇬🇧" if language == 'en' else "Türkçe 🇹🇷"))
            print("The program will automatically create and upload videos" if language == 'en' else "Program, GPT tarafından üretilen konulara göre otomatik olarak")
            print("based on topics generated by GPT." if language == 'en' else "video oluşturup YouTube'a yükleyecek.")
            print("Press Ctrl+C to stop." if language == 'en' else "Durdurmak için Ctrl+C tuşlarına basın.")
            print(f"{'='*50}\n")
            time.sleep(2)
        
        # Set a reasonable timeout for the event loop
        exit_code = asyncio.run(async_main(continuous_mode, max_videos, language), debug=False)
        
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
