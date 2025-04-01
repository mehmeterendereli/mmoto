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
        
        # Direkt olarak filter_complex kullanarak videoları birleştirme (en güvenilir yöntem)
        filter_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -i "{os.path.abspath(closing_video_path)}" -filter_complex "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]" -map "[outv]" -map "[outa]" -c:v libx264 -c:a aac "{os.path.abspath(final_video)}"'
        
        try:
            # Direct filter_complex yöntemi
            print("Filter complex yöntemi kullanılıyor...")
            subprocess.run(filter_cmd, shell=True, check=True)
            
            # Başarılı mı kontrol et
            if os.path.exists(final_video) and os.path.getsize(final_video) > 0:
                print(f"Kapanış sahnesi başarıyla eklendi: {final_video}")
                return final_video
            else:
                raise Exception("Filter complex başarısız")
                
        except Exception as e:
            print(f"Filter complex hatası: {str(e)}")
            
            # İkinci yöntem: TS formatına dönüştürme
            print("TS formatı yöntemi deneniyor...")
            video1_ts = os.path.join(project_folder, "video1.ts")
            video2_ts = os.path.join(project_folder, "video2.ts")
            
            # Videoları TS formatına açıkça ses kanalını koruyarak dönüştür
            ts1_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -c:v copy -c:a copy -bsf:v h264_mp4toannexb -f mpegts "{os.path.abspath(video1_ts)}"'
            ts2_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(closing_video_path)}" -c:v copy -c:a copy -bsf:v h264_mp4toannexb -f mpegts "{os.path.abspath(video2_ts)}"'
            
            try:
                # Video 1 TS'e dönüştür
                subprocess.run(ts1_cmd, shell=True, check=True)
                # Video 2 TS'e dönüştür
                subprocess.run(ts2_cmd, shell=True, check=True)
                
                # İki TS dosyasını birleştir, ses kanalını koru
                concat_cmd = f'"{ffmpeg_path}" -i "concat:{os.path.abspath(video1_ts)}|{os.path.abspath(video2_ts)}" -c:v copy -c:a copy -bsf:a aac_adtstoasc "{os.path.abspath(final_video)}"'
                subprocess.run(concat_cmd, shell=True, check=True)
                
                # Başarılı mı kontrol et
                if os.path.exists(final_video) and os.path.getsize(final_video) > 0:
                    print(f"Kapanış sahnesi başarıyla eklendi (TS yöntemi): {final_video}")
                else:
                    raise Exception("TS birleştirme başarısız")
                
                # Geçici dosyaları temizle
                try:
                    for temp_file in [video1_ts, video2_ts]:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                except Exception as e:
                    print(f"Geçici dosya silme hatası: {str(e)}")
                
                return final_video
                    
            except Exception as ts_error:
                print(f"TS dönüştürme hatası: {str(ts_error)}")
                
                # Üçüncü yöntem: MP4Box kullanarak birleştirme
                print("Liste dosyası yöntemi deneniyor...")
                try:
                    # Liste dosyası oluştur
                    list_file_path = os.path.join(project_folder, "concat_list.txt")
                    with open(list_file_path, 'w', encoding='utf-8') as f:
                        f.write(f"file '{os.path.abspath(video_path)}'\n")
                        f.write(f"file '{os.path.abspath(closing_video_path)}'\n")
                    
                    # Liste dosyasını kullanarak birleştir
                    list_cmd = f'"{ffmpeg_path}" -f concat -safe 0 -i "{list_file_path}" -c copy "{os.path.abspath(final_video)}"'
                    subprocess.run(list_cmd, shell=True, check=True)
                    
                    # Başarılı mı kontrol et
                    if os.path.exists(final_video) and os.path.getsize(final_video) > 0:
                        print(f"Kapanış sahnesi başarıyla eklendi (Liste yöntemi): {final_video}")
                    else:
                        raise Exception("Liste birleştirme başarısız")
                    
                    # Geçici dosyaları temizle
                    try:
                        if os.path.exists(list_file_path):
                            os.remove(list_file_path)
                    except Exception as e:
                        print(f"Geçici dosya silme hatası: {str(e)}")
                    
                    return final_video
                
                except Exception as list_error:
                    print(f"Liste dosyası hatası: {str(list_error)}")
                    # Son çare olarak orijinal videoyu kopyala
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