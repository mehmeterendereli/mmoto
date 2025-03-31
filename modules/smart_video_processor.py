#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import subprocess
import logging
import time
from typing import Dict, List, Any, Tuple

logger = logging.getLogger('merak_makinesi')

def get_ffmpeg_paths() -> Tuple[str, str]:
    """
    config.json dosyasından FFmpeg ve FFprobe yollarını alır
    
    Returns:
        Tuple[str, str]: FFmpeg ve FFprobe yolları
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    ffmpeg_path = "ffmpeg"
    ffprobe_path = "ffprobe"
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                
                if "ffmpeg_path" in config:
                    ffmpeg_path = config["ffmpeg_path"]
                
                if "ffprobe_path" in config:
                    ffprobe_path = config["ffprobe_path"]
        except Exception as e:
            logger.error(f"FFmpeg yolları yükleme hatası: {str(e)}")
    
    return ffmpeg_path, ffprobe_path

def process_media_based_on_storyboard(media_mapping: Dict[str, Any], project_folder: str, resolution: Tuple[int, int] = (1080, 1920)) -> str:
    """
    Storyboard'a göre medya dosyalarını işler
    
    Args:
        media_mapping (Dict[str, Any]): Medya eşleme bilgileri
        project_folder (str): Proje klasörünün yolu
        resolution (Tuple[int, int], optional): Video çözünürlüğü (genişlik, yükseklik).
            Varsayılan değer (1080, 1920).
    
    Returns:
        str: İşlenmiş ana video dosyasının yolu
    """
    ffmpeg_path, ffprobe_path = get_ffmpeg_paths()
    processed_scenes = []
    scenes = media_mapping.get("scenes", [])
    
    if not scenes:
        logger.error("İşlenecek sahne bulunamadı!")
        return create_empty_video(project_folder, resolution, ffmpeg_path)
    
    # Her sahne için işleme yap
    for i, scene in enumerate(scenes):
        try:
            scene_id = scene.get("scene_id", i)
            media_file = scene.get("media_file", "")
            media_type = scene.get("media_type", "none")
            duration = scene.get("duration", 5)
            
            if not media_file or not os.path.exists(media_file):
                logger.warning(f"Sahne {scene_id} için medya dosyası bulunamadı: {media_file}")
                continue
            
            # İşlenmiş sahne dosyasının yolu
            output_file = os.path.join(project_folder, f"processed_scene_{scene_id}.mp4")
            
            # Medya türüne göre işleme
            if media_type == "video":
                # Video işle
                process_video_scene(media_file, output_file, duration, resolution, ffmpeg_path, ffprobe_path, scene)
            else:
                # Fotoğraf işle (video haline getir)
                process_photo_scene(media_file, output_file, duration, resolution, ffmpeg_path, scene)
            
            # İşlenen sahneleri listele
            if os.path.exists(output_file):
                processed_scenes.append({
                    "file": output_file,
                    "duration": duration,
                    "scene_id": scene_id,
                    "text": scene.get("text", "")
                })
                logger.info(f"Sahne {scene_id} başarıyla işlendi: {output_file}")
            else:
                logger.error(f"Sahne {scene_id} işleme hatası!")
        
        except Exception as e:
            logger.error(f"Sahne {i} işleme hatası: {str(e)}")
    
    # İşlenen sahneleri birleştir
    if processed_scenes:
        return join_processed_scenes(processed_scenes, project_folder, ffmpeg_path)
    else:
        logger.error("İşlenmiş sahne bulunamadı!")
        return create_empty_video(project_folder, resolution, ffmpeg_path)

def process_video_scene(video_path: str, output_file: str, duration: float, resolution: Tuple[int, int], 
                        ffmpeg_path: str, ffprobe_path: str, scene_info: Dict[str, Any]) -> None:
    """
    Video sahnesini işler
    
    Args:
        video_path (str): Video dosyası yolu
        output_file (str): Çıktı dosyası yolu
        duration (float): İstenen süre (saniye)
        resolution (Tuple[int, int]): Video çözünürlüğü (genişlik, yükseklik)
        ffmpeg_path (str): FFmpeg yolu
        ffprobe_path (str): FFprobe yolu
        scene_info (Dict[str, Any]): Sahne bilgileri
    """
    try:
        # Video süresi ve boyutlarını al
        probe_cmd = f'"{ffprobe_path}" -v error -select_streams v:0 -show_entries stream=width,height,duration -of json "{video_path}"'
        result = subprocess.run(probe_cmd, shell=True, capture_output=True, text=True)
        info = json.loads(result.stdout)
        
        width = int(info["streams"][0]["width"])
        height = int(info["streams"][0]["height"])
        
        # Süreyi kontrol et
        if "duration" in info["streams"][0]:
            original_duration = float(info["streams"][0]["duration"])
        else:
            # Format bölümünden süreyi al
            format_cmd = f'"{ffprobe_path}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
            result = subprocess.run(format_cmd, shell=True, capture_output=True, text=True)
            original_duration = float(result.stdout.strip())
        
        # Video 9:16 formatına uygun değilse kırp/ölçeklendir
        if width / height != resolution[0] / resolution[1]:
            # Sahne için kamera hareketi belirle
            camera_movement = scene_info.get("camera_movement", "static")
            
            if camera_movement == "zoom_in":
                # Yakınlaştırma efekti (başlangıçta geniş, sonda yakın)
                zoom_filter = f"zoompan=z='min(zoom+0.0015,1.5)':d={int(duration*30)}:s={resolution[0]}x{resolution[1]}"
                filter_complex = f"crop={height*9/16}:{height}:(iw-{height*9/16})/2:0,scale={resolution[0]}:{resolution[1]},{zoom_filter}"
            elif camera_movement == "zoom_out":
                # Uzaklaştırma efekti (başlangıçta yakın, sonda geniş)
                zoom_filter = f"zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d={int(duration*30)}:s={resolution[0]}x{resolution[1]}"
                filter_complex = f"crop={height*9/16}:{height}:(iw-{height*9/16})/2:0,scale={resolution[0]}:{resolution[1]},{zoom_filter}"
            elif camera_movement == "pan_left":
                # Sola pan
                filter_complex = f"crop={height*9/16}:{height}:min(iw-{height*9/16},max(0,iw-{height*9/16})*t/{duration}):0,scale={resolution[0]}:{resolution[1]}"
            elif camera_movement == "pan_right":
                # Sağa pan
                filter_complex = f"crop={height*9/16}:{height}:max(0,iw-{height*9/16})*(1-t/{duration}):0,scale={resolution[0]}:{resolution[1]}"
            else:
                # Statik - ortadan kırp
                filter_complex = f"crop={height*9/16}:{height}:(iw-{height*9/16})/2:0,scale={resolution[0]}:{resolution[1]}"
        else:
            # Zaten 9:16 formatındaysa sadece ölçeklendir
            filter_complex = f"scale={resolution[0]}:{resolution[1]}"
        
        # Başlangıç zamanını belirle
        if original_duration > duration:
            # Daha uzun videolarda ortadan al
            start_time = (original_duration - duration) / 2
        else:
            # Kısa videolarda baştan başla
            start_time = 0
            # Kısa videoyu döngüye al
            if original_duration < duration:
                loop_count = int(duration / original_duration) + 1
                filter_complex = f"loop={loop_count}:1:0,{filter_complex}"
        
        # Komutu oluştur ve çalıştır
        cmd = f'"{ffmpeg_path}" -i "{video_path}" -ss {start_time} -t {min(duration, original_duration)} -vf "{filter_complex}" -c:v libx264 -preset medium -crf 22 -r 30 -pix_fmt yuv420p -y "{output_file}"'
        subprocess.run(cmd, shell=True, check=True)
        
    except Exception as e:
        logger.error(f"Video sahnesi işleme hatası: {str(e)}")
        raise

def process_photo_scene(photo_path: str, output_file: str, duration: float, resolution: Tuple[int, int], 
                       ffmpeg_path: str, scene_info: Dict[str, Any]) -> None:
    """
    Fotoğraf sahnesini video olarak işler
    
    Args:
        photo_path (str): Fotoğraf dosyası yolu
        output_file (str): Çıktı dosyası yolu
        duration (float): İstenen süre (saniye)
        resolution (Tuple[int, int]): Video çözünürlüğü (genişlik, yükseklik)
        ffmpeg_path (str): FFmpeg yolu
        scene_info (Dict[str, Any]): Sahne bilgileri
    """
    try:
        # Fotoğraf için kamera hareketi belirle
        camera_movement = scene_info.get("camera_movement", "ken_burns")
        
        if camera_movement == "ken_burns":
            # Ken Burns efekti (yavaş yakınlaştırma ve pan)
            filter_complex = f"zoompan=z='min(max(1,1.2*in_w/iw),1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*30)}:s={resolution[0]}x{resolution[1]}"
        elif camera_movement == "zoom_in":
            # Yakınlaştırma efekti
            filter_complex = f"zoompan=z='min(zoom+0.002,1.5)':d={int(duration*30)}:s={resolution[0]}x{resolution[1]}"
        elif camera_movement == "zoom_out":
            # Uzaklaştırma efekti
            filter_complex = f"zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.002))':d={int(duration*30)}:s={resolution[0]}x{resolution[1]}"
        elif camera_movement == "pan_left":
            # Sola pan
            filter_complex = f"zoompan=z='1.1':x='max(0,iw-iw/zoom-(iw-iw/zoom)*t/{duration})':y='ih/2-(ih/zoom/2)':d={int(duration*30)}:s={resolution[0]}x{resolution[1]}"
        elif camera_movement == "pan_right":
            # Sağa pan
            filter_complex = f"zoompan=z='1.1':x='min(iw-iw/zoom,(iw-iw/zoom)*t/{duration})':y='ih/2-(ih/zoom/2)':d={int(duration*30)}:s={resolution[0]}x{resolution[1]}"
        else:
            # Statik
            filter_complex = f"scale={resolution[0]}:{resolution[1]}:force_original_aspect_ratio=decrease,pad={resolution[0]}:{resolution[1]}:(ow-iw)/2:(oh-ih)/2"
        
        # Komutu oluştur ve çalıştır
        cmd = f'"{ffmpeg_path}" -loop 1 -i "{photo_path}" -vf "{filter_complex}" -c:v libx264 -preset medium -crf 22 -r 30 -pix_fmt yuv420p -t {duration} -y "{output_file}"'
        subprocess.run(cmd, shell=True, check=True)
        
    except Exception as e:
        logger.error(f"Fotoğraf sahnesi işleme hatası: {str(e)}")
        raise

def join_processed_scenes(scenes: List[Dict[str, Any]], project_folder: str, ffmpeg_path: str) -> str:
    """
    İşlenen sahneleri tek bir videoda birleştirir
    
    Args:
        scenes (List[Dict[str, Any]]): İşlenen sahneler
        project_folder (str): Proje klasörünün yolu
        ffmpeg_path (str): FFmpeg yolu
    
    Returns:
        str: Birleştirilmiş video dosyasının yolu
    """
    # Sahneleri sıralama
    scenes.sort(key=lambda x: x["scene_id"])
    
    # Sahne listesi dosyası oluştur
    scenes_list_path = os.path.join(project_folder, "scenes_list.txt")
    with open(scenes_list_path, "w", encoding="utf-8") as f:
        for scene in scenes:
            f.write(f"file '{os.path.abspath(scene['file'])}'\n")
    
    # Birleştirilmiş video dosyasının yolu
    output_file = os.path.join(project_folder, "processed_video.mp4")
    
    try:
        # Sahneleri birleştir
        cmd = f'"{ffmpeg_path}" -f concat -safe 0 -i "{scenes_list_path}" -c copy -y "{output_file}"'
        subprocess.run(cmd, shell=True, check=True)
        
        # Birleştirilen video var mı kontrol et
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logger.info(f"Sahneler başarıyla birleştirildi: {output_file}")
            return output_file
        else:
            logger.error("Sahneleri birleştirme başarısız oldu!")
            return create_empty_video(project_folder, (1080, 1920), ffmpeg_path)
    
    except Exception as e:
        logger.error(f"Sahneleri birleştirme hatası: {str(e)}")
        return create_empty_video(project_folder, (1080, 1920), ffmpeg_path)

def create_empty_video(project_folder: str, resolution: Tuple[int, int], ffmpeg_path: str) -> str:
    """
    Boş bir video oluşturur
    
    Args:
        project_folder (str): Proje klasörünün yolu
        resolution (Tuple[int, int]): Video çözünürlüğü (genişlik, yükseklik)
        ffmpeg_path (str): FFmpeg yolu
    
    Returns:
        str: Boş video dosyasının yolu
    """
    output_file = os.path.join(project_folder, "processed_video.mp4")
    
    try:
        # Siyah arkaplan ile 10 saniyelik boş video oluştur
        cmd = f'"{ffmpeg_path}" -f lavfi -i color=c=black:s={resolution[0]}x{resolution[1]}:r=30 -t 10 -c:v libx264 -preset medium -crf 22 -pix_fmt yuv420p -y "{output_file}"'
        subprocess.run(cmd, shell=True, check=True)
        
        logger.info(f"Boş video oluşturuldu: {output_file}")
        return output_file
    
    except Exception as e:
        logger.error(f"Boş video oluşturma hatası: {str(e)}")
        # Son çare: Boş dosya oluştur
        with open(output_file, "wb") as f:
            pass
        return output_file

def generate_production_instructions(media_mapping: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """
    Gelişmiş video üretim yönergeleri oluşturur
    
    Args:
        media_mapping (Dict[str, Any]): Medya eşleme bilgileri
        api_key (str): OpenAI API anahtarı
    
    Returns:
        Dict[str, Any]: Üretim yönergeleri
    """
    # Bu fonksiyon daha gelişmiş versiyonda OpenAI ile entegre edilecek
    # Şimdilik basit bir şekilde varsayılan yönergeler döndürür
    
    scenes = media_mapping.get("scenes", [])
    instructions = {
        "scenes": [],
        "transitions": "crossfade",
        "default_duration": 5
    }
    
    for i, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", i)
        media_type = scene.get("media_type", "video")
        camera_movement = "ken_burns" if media_type == "photo" else "static"
        
        # Varyasyon için kamera hareketleri
        if i % 3 == 0:
            camera_movement = "zoom_in"
        elif i % 3 == 1:
            camera_movement = "pan_left" if media_type == "video" else "zoom_out"
        
        instructions["scenes"].append({
            "scene_id": scene_id,
            "media_type": media_type,
            "camera_movement": camera_movement,
            "duration": scene.get("duration", 5),
            "transitions": "crossfade" if i > 0 else "fade_in"
        })
    
    return instructions 