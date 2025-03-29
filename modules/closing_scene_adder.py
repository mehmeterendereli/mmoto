#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import shutil
import json

def add_closing_scene(video_path: str, closing_video_path: str, project_folder: str) -> str:
    """
    Videoya kapanış videosu ekler
    
    Args:
        video_path (str): Ana video dosyasının yolu
        closing_video_path (str): Kapanış video dosyasının yolu
        project_folder (str): Proje klasörünün yolu
    
    Returns:
        str: Final video dosyasının yolu
    """
    # FFmpeg yolunu config.json'dan al
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    ffmpeg_path = "ffmpeg"
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                
                if "ffmpeg_path" in config:
                    ffmpeg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config["ffmpeg_path"])
        except:
            pass
    
    # Final video dosyasının yolu
    final_video = os.path.join(project_folder, "final_video.mp4")
    
    if not os.path.exists(video_path):
        print(f"Hata: Video dosyası bulunamadı: {video_path}")
        # Boş bir dosya oluştur
        with open(final_video, 'wb') as f:
            f.write(b'')
        return final_video
    
    try:
        # Kapanış videosunun varlığını kontrol et
        if not os.path.exists(closing_video_path):
            print(f"Uyarı: Kapanış videosu bulunamadı: {closing_video_path}")
            # Alternatif kapanış videosu varmı diye bak
            alt_closing_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "kapanis.mp4")
            if os.path.exists(alt_closing_path):
                closing_video_path = alt_closing_path
                print(f"Alternatif kapanış videosu kullanılacak: {closing_video_path}")
            else:
                # Kapanış videosu yoksa ana videoyu döndür
                shutil.copy2(video_path, final_video)
                return final_video
        
        print("Kapanış sahnesi ekleniyor...")
        
        # Her iki videoyu da doğrudan birleştirmek yerine önce formatları eşleştirelim
        # Ana video formatını al
        temp_closing = os.path.join(project_folder, "temp_closing.mp4")
        try:
            probe_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -show_streams -select_streams v -show_format -print_format json'
            probe_result = subprocess.run(probe_cmd, shell=True, capture_output=True, text=True)
            video_info = json.loads(probe_result.stdout)
            
            # Ana videonun özelliklerini kapat
            width = 1080
            height = 1920
            if 'streams' in video_info and video_info['streams']:
                width = video_info['streams'][0].get('width', 1080)
                height = video_info['streams'][0].get('height', 1920)
            
            # Kapanış videosunu aynı formata dönüştür
            convert_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(closing_video_path)}" -vf "scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2" -c:v libx264 -pix_fmt yuv420p "{os.path.abspath(temp_closing)}"'
            subprocess.run(convert_cmd, shell=True, check=True)
            
            # Kapanış videosu başarıyla dönüştürüldüyse, onu kullan
            if os.path.exists(temp_closing) and os.path.getsize(temp_closing) > 0:
                closing_video_path = temp_closing
            
        except Exception as e:
            print(f"Video bilgisi alınamadı veya dönüştürme hatası: {str(e)}")
        
        # İki video arasında, filtergraph olmadan, temp dosyaları kullanarak işlem yap
        # Her iki videoyu da TS formatına dönüştürelim
        video1_ts = os.path.join(project_folder, "video1.ts")
        video2_ts = os.path.join(project_folder, "video2.ts")
        
        # Videoları TS formatına dönüştür
        ts1_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -c copy -bsf:v h264_mp4toannexb -f mpegts "{os.path.abspath(video1_ts)}"'
        ts2_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(closing_video_path)}" -c copy -bsf:v h264_mp4toannexb -f mpegts "{os.path.abspath(video2_ts)}"'
        
        try:
            # Video 1 TS'e dönüştür
            subprocess.run(ts1_cmd, shell=True, check=True)
            # Video 2 TS'e dönüştür
            subprocess.run(ts2_cmd, shell=True, check=True)
            
            # İki TS dosyasını birleştirerek MP4 oluştur
            concat_cmd = f'"{ffmpeg_path}" -i "concat:{os.path.abspath(video1_ts)}|{os.path.abspath(video2_ts)}" -c copy -bsf:a aac_adtstoasc "{os.path.abspath(final_video)}"'
            subprocess.run(concat_cmd, shell=True, check=True)
            
            # Başarılı mı kontrol et
            if os.path.exists(final_video) and os.path.getsize(final_video) > 0:
                print(f"Kapanış sahnesi başarıyla eklendi: {final_video}")
            else:
                raise Exception("Final video oluşturulamadı")
                
        except Exception as e:
            print(f"TS birleştirme hatası: {str(e)}")
            try:
                # Başarısız olursa alternatif yöntem dene - filter_complex
                filter_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -i "{os.path.abspath(closing_video_path)}" -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" -map "[outv]" "{os.path.abspath(final_video)}"'
                subprocess.run(filter_cmd, shell=True, check=True)
                
                if os.path.exists(final_video) and os.path.getsize(final_video) > 0:
                    print("Alternatif birleştirme başarılı")
                else:
                    raise Exception("Alternatif birleştirme başarısız")
            except Exception as filter_error:
                print(f"Filter birleştirme hatası: {str(filter_error)}")
                # Son çare olarak orijinal videoyu kopyala
                shutil.copy2(video_path, final_video)
                print(f"Birleştirme başarısız, orijinal video kullanıldı: {final_video}")
        
        # Geçici dosyaları temizle
        try:
            for temp_file in [video1_ts, video2_ts, temp_closing]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        except Exception as e:
            print(f"Geçici dosya silme hatası: {str(e)}")
        
        return final_video
        
    except Exception as e:
        print(f"Kapanış sahnesi ekleme hatası: {str(e)}")
        
        # Hata durumunda ana videoyu final_video olarak kopyala
        try:
            shutil.copy2(video_path, final_video)
            return final_video
        except Exception as copy_error:
            print(f"Dosya kopyalama hatası: {str(copy_error)}")
            # Son çare - boş dosya
            with open(final_video, 'wb') as f:
                f.write(b'')
            return final_video 