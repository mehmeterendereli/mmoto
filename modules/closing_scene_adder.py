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
    ffprobe_path = "ffmpeg"
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                
                if "ffmpeg_path" in config:
                    ffmpeg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config["ffmpeg_path"])
                
                if "ffprobe_path" in config:
                    ffprobe_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config["ffprobe_path"])
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
        
        # Her iki videonun da çözünürlüğünü belirle
        try:
            # Ana video çözünürlüğü
            video_info_cmd = f'"{ffprobe_path}" -v error -select_streams v:0 -show_entries stream=width,height -of json "{os.path.abspath(video_path)}"'
            result = subprocess.run(video_info_cmd, shell=True, capture_output=True, text=True)
            video_info = json.loads(result.stdout)
            video_width = int(video_info["streams"][0]["width"])
            video_height = int(video_info["streams"][0]["height"])
            
            # Kapanış videosu çözünürlüğü
            closing_info_cmd = f'"{ffprobe_path}" -v error -select_streams v:0 -show_entries stream=width,height -of json "{os.path.abspath(closing_video_path)}"'
            result = subprocess.run(closing_info_cmd, shell=True, capture_output=True, text=True)
            closing_info = json.loads(result.stdout)
            closing_width = int(closing_info["streams"][0]["width"])
            closing_height = int(closing_info["streams"][0]["height"])
            
            print(f"Ana video çözünürlüğü: {video_width}x{video_height}")
            print(f"Kapanış videosu çözünürlüğü: {closing_width}x{closing_height}")
            
            # Çözünürlükler farklı ise, kapanış videosunu ana video çözünürlüğüne ölçekle
            if video_width != closing_width or video_height != closing_height:
                print(f"Çözünürlük farklı! Kapanış videosunu {video_width}x{video_height} çözünürlüğüne ölçekliyorum.")
                
                # Çözünürlük eşitleme için geçici video oluştur
                scaled_closing_path = os.path.join(project_folder, "scaled_closing.mp4")
                scale_cmd = f'"{ffmpeg_path}" -y -i "{os.path.abspath(closing_video_path)}" -vf "scale={video_width}:{video_height},setsar=1:1" -c:v libx264 -preset fast -crf 22 -c:a aac -strict experimental "{os.path.abspath(scaled_closing_path)}"'
                
                subprocess.run(scale_cmd, shell=True, check=True)
                
                # Ölçeklenmiş video varlığını kontrol et
                if os.path.exists(scaled_closing_path) and os.path.getsize(scaled_closing_path) > 0:
                    closing_video_path = scaled_closing_path
                    print(f"Kapanış videosu başarıyla ölçeklendi: {scaled_closing_path}")
                    
        except Exception as e:
            print(f"Video bilgisi alınamadı: {str(e)}")
            # Hata oluşursa devam et, FFmpeg birleştirme işlemi muhtemelen hata verecek

        # Videolar hazır, şimdi birleştirme işlemi yap
        # Concat demuxer kullanacağız - çözünürlüklerin eşit olması gerekir
        concat_list_path = os.path.join(project_folder, "concat_list.txt")
        with open(concat_list_path, 'w', encoding='utf-8') as f:
            f.write(f"file '{os.path.abspath(video_path)}'\n")
            f.write(f"file '{os.path.abspath(closing_video_path)}'\n")
        
        # Concat demuxer komutu
        concat_cmd = f'"{ffmpeg_path}" -y -f concat -safe 0 -i "{os.path.abspath(concat_list_path)}" -c copy "{os.path.abspath(final_video)}"'
        
        try:
            print("Concat demuxer yöntemi kullanılıyor...")
            print(f"Birleştirme komutu: {concat_cmd}")
            subprocess.run(concat_cmd, shell=True, check=True)
            
            # Başarılı mı kontrol et
            if os.path.exists(final_video) and os.path.getsize(final_video) > 0:
                print(f"Kapanış sahnesi başarıyla eklendi: {final_video}")
                
                # Geçici dosyaları temizle
                if os.path.exists(concat_list_path):
                    os.remove(concat_list_path)
                if os.path.exists(os.path.join(project_folder, "scaled_closing.mp4")):
                    os.remove(os.path.join(project_folder, "scaled_closing.mp4"))
                
                return final_video
            else:
                raise Exception("Concat demuxer başarısız")
                
        except Exception as e:
            print(f"Concat demuxer hatası: {str(e)}")
            
            # İkinci yöntem: Filter complex ile birleştirme
            print("Filter complex yöntemi deneniyor...")
            
            # Filter complex komutu - çözünürlük uyumsuzluğunu ele alır
            filter_cmd = f'"{ffmpeg_path}" -y -i "{os.path.abspath(video_path)}" -i "{os.path.abspath(closing_video_path)}" -filter_complex "[0:v]setsar=1:1[v1]; [1:v]scale={video_width}:{video_height},setsar=1:1[v2]; [v1][0:a][v2][1:a]concat=n=2:v=1:a=1[outv][outa]" -map "[outv]" -map "[outa]" -c:v libx264 -preset fast -crf 22 -c:a aac -strict experimental "{os.path.abspath(final_video)}"'
            
            try:
                subprocess.run(filter_cmd, shell=True, check=True)
                
                # Başarılı mı kontrol et
                if os.path.exists(final_video) and os.path.getsize(final_video) > 0:
                    print(f"Kapanış sahnesi başarıyla eklendi (filter complex): {final_video}")
                    
                    # Geçici dosyaları temizle
                    if os.path.exists(os.path.join(project_folder, "scaled_closing.mp4")):
                        os.remove(os.path.join(project_folder, "scaled_closing.mp4"))
                    
                    return final_video
                else:
                    raise Exception("Filter complex başarısız")
                    
            except Exception as filter_error:
                print(f"Filter complex hatası: {str(filter_error)}")
                
                # Son çare: TS formatını dene
                print("TS formatı yöntemi deneniyor...")
                
                video1_ts = os.path.join(project_folder, "video1.ts")
                video2_ts = os.path.join(project_folder, "video2.ts")
                
                # Her iki videoyu da aynı çözünürlüğe getirip TS formatına dönüştür
                ts1_cmd = f'"{ffmpeg_path}" -y -i "{os.path.abspath(video_path)}" -c:v libx264 -c:a aac -strict experimental "{os.path.abspath(video1_ts)}"'
                ts2_cmd = f'"{ffmpeg_path}" -y -i "{os.path.abspath(closing_video_path)}" -vf "scale={video_width}:{video_height}" -c:v libx264 -c:a aac -strict experimental "{os.path.abspath(video2_ts)}"'
                
                try:
                    # Video 1 TS'e dönüştür
                    subprocess.run(ts1_cmd, shell=True, check=True)
                    # Video 2 TS'e dönüştür
                    subprocess.run(ts2_cmd, shell=True, check=True)
                    
                    # İki TS dosyasını birleştir
                    concat_ts_cmd = f'"{ffmpeg_path}" -y -i "concat:{os.path.abspath(video1_ts)}|{os.path.abspath(video2_ts)}" -c copy "{os.path.abspath(final_video)}"'
                    subprocess.run(concat_ts_cmd, shell=True, check=True)
                    
                    # Başarılı mı kontrol et
                    if os.path.exists(final_video) and os.path.getsize(final_video) > 0:
                        print(f"Kapanış sahnesi başarıyla eklendi (TS yöntemi): {final_video}")
                    else:
                        raise Exception("TS birleştirme başarısız")
                    
                    # Geçici dosyaları temizle
                    for temp_file in [video1_ts, video2_ts, os.path.join(project_folder, "scaled_closing.mp4")]:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    
                    return final_video
                
                except Exception as ts_error:
                    print(f"TS dönüştürme hatası: {str(ts_error)}")
                    
                    # Tüm yöntemler başarısız olursa orijinal videoyu döndür
                    shutil.copy2(video_path, final_video)
                    print(f"Tüm birleştirme yöntemleri başarısız, orijinal video kullanıldı: {final_video}")
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