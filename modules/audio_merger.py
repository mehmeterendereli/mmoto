#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
from typing import List
import tempfile
import shutil
import json

def merge_audio(video_path: str, audio_files: List[str], project_folder: str) -> str:
    """
    TTS seslerini birleştirip videoya ekler
    
    Args:
        video_path (str): Ses eklenecek video dosyasının yolu
        audio_files (List[str]): Eklenecek ses dosyalarının yolları
        project_folder (str): Proje klasörünün yolu
    
    Returns:
        str: Ses eklenmiş video dosyasının yolu
    """
    # FFmpeg yolunu config.json'dan al
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    ffmpeg_path = "ffmpeg"
    ffprobe_path = "ffprobe"
    
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
    
    if not os.path.exists(video_path):
        print(f"Hata: Video dosyası bulunamadı: {video_path}")
        # Boş bir video dosyası oluştur
        audio_video = os.path.join(project_folder, "video_with_audio.mp4")
        with open(audio_video, 'wb') as f:
            f.write(b'')
        return audio_video
    
    if not audio_files:
        print("Uyarı: Eklenecek ses dosyası bulunamadı!")
        # Sadece videoyu döndür
        audio_video = os.path.join(project_folder, "video_with_audio.mp4")
        shutil.copy2(video_path, audio_video)
        return audio_video
    
    try:
        # Ses eklenmiş video dosyasının yolu
        audio_video = os.path.join(project_folder, "video_with_audio.mp4")
        
        # Video ve ses sürelerini kontrol et
        video_duration = 0
        audio_duration = 0
        
        # Video süresini al
        try:
            video_duration_cmd = f'"{ffprobe_path}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{os.path.abspath(video_path)}"'
            video_result = subprocess.run(video_duration_cmd, shell=True, capture_output=True, text=True)
            video_duration = float(video_result.stdout.strip())
            print(f"Video süresi: {video_duration:.2f} saniye")
        except Exception as e:
            print(f"Video süresi hesaplama hatası: {str(e)}")
        
        # Ses dosyalarının toplam süresini hesapla
        for audio_file in audio_files:
            try:
                audio_duration_cmd = f'"{ffprobe_path}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{os.path.abspath(audio_file)}"'
                audio_result = subprocess.run(audio_duration_cmd, shell=True, capture_output=True, text=True)
                file_duration = float(audio_result.stdout.strip())
                audio_duration += file_duration
            except Exception as e:
                print(f"Ses süresi hesaplama hatası: {str(e)}")
        
        print(f"Toplam ses süresi: {audio_duration:.2f} saniye")
        
        # Ses ve video süresi uyumsuzluğunu kontrol et ve gerekirse uyum sağla
        # Eğer ses video süresinden daha uzunsa, videoyu yavaşlat
        # Eğer video ses süresinden çok daha uzunsa, videoyu kırp
        if audio_duration > 3 and video_duration > 3:  # Her ikisi de geçerli uzunlukta
            if audio_duration > video_duration * 1.02:  # Ses %2'den fazla uzunsa (daha hassas)
                print(f"Uyarı: Ses süresi video süresinden %{((audio_duration / video_duration) - 1) * 100:.1f} daha uzun")
                print("Video sesi uyumlu hale getirmek için düzenlenecek...")
                
                # Videoyu yavaşlat ve ses süresine uygun hale getir
                speed_factor = video_duration / audio_duration
                adjusted_video = os.path.join(project_folder, "adjusted_video.mp4")
                
                # Daha hassas hız ayarı için atempo filtresi ekle
                adjust_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -filter:v "setpts={1/speed_factor}*PTS" -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p "{os.path.abspath(adjusted_video)}"'
                
                try:
                    subprocess.run(adjust_cmd, shell=True, check=True)
                    if os.path.exists(adjusted_video) and os.path.getsize(adjusted_video) > 0:
                        video_path = adjusted_video
                        print(f"Video sese uygun şekilde yavaşlatıldı: {adjusted_video}")
                except Exception as adjust_error:
                    print(f"Video düzenleme hatası: {str(adjust_error)}")
        
            elif video_duration > audio_duration * 1.05:  # Video %5'den fazla uzunsa (daha hassas)
                print(f"Uyarı: Video süresi ses süresinden %{((video_duration / audio_duration) - 1) * 100:.1f} daha uzun")
                print("Video sese uyumlu hale getirmek için kırpılacak...")
                
                # Video süresini sese uygun şekilde kırp
                trimmed_video = os.path.join(project_folder, "trimmed_video.mp4")
                
                # Videoyu ses süresine göre kırp, %10 tolerans ekle (daha hassas)
                trim_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -t {audio_duration * 1.10} -c:v copy "{os.path.abspath(trimmed_video)}"'
                
                try:
                    subprocess.run(trim_cmd, shell=True, check=True)
                    if os.path.exists(trimmed_video) and os.path.getsize(trimmed_video) > 0:
                        video_path = trimmed_video
                        print(f"Video sese uygun şekilde kırpıldı: {trimmed_video}")
                except Exception as trim_error:
                    print(f"Video kırpma hatası: {str(trim_error)}")
        
        # Önce ses dosyalarını tek bir ses dosyasında birleştir
        merged_audio = os.path.join(project_folder, "merged_audio.mp3")
        
        if len(audio_files) == 1:
            # Tek ses dosyası varsa kopyala
            shutil.copy2(audio_files[0], merged_audio)
        else:
            # Birden fazla ses dosyası varsa birleştir
            # Concat demuxer liste dosyası oluştur
            concat_list = os.path.join(project_folder, "concat_list.txt")
            with open(concat_list, "w", encoding="utf-8") as f:
                for audio_file in audio_files:
                    if os.path.exists(audio_file):
                        f.write(f"file '{os.path.abspath(audio_file)}'\n")
            
            # Sesleri birleştir
            concat_cmd = f'"{ffmpeg_path}" -f concat -safe 0 -i "{os.path.abspath(concat_list)}" -c copy "{os.path.abspath(merged_audio)}"'
            try:
                print("Ses dosyaları birleştiriliyor...")
                subprocess.run(concat_cmd, shell=True, check=True)
            except Exception as e:
                print(f"Ses birleştirme hatası: {str(e)}")
                if len(audio_files) > 0 and os.path.exists(audio_files[0]):
                    shutil.copy2(audio_files[0], merged_audio)
                else:
                    # Boş ses dosyası oluştur
                    with open(merged_audio, 'wb') as f:
                        f.write(b'')
        
        # Birleştirilen sesi videoya ekle
        if os.path.exists(merged_audio) and os.path.getsize(merged_audio) > 0:
            print("Ses videoya ekleniyor...")
            
            # Video uzatma stratejisi: Son kareyi 3 saniye daha uzat
            extended_video = os.path.join(project_folder, "extended_video.mp4")
            # Son kareyi 3 saniye daha uzat
            extend_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -filter_complex "[0:v]tpad=stop_mode=clone:stop_duration=3[v]" -map "[v]" -c:v libx264 -pix_fmt yuv420p "{os.path.abspath(extended_video)}"'
            
            try:
                # Videoyu uzat
                subprocess.run(extend_cmd, shell=True, check=True)
                if os.path.exists(extended_video) and os.path.getsize(extended_video) > 0:
                    print(f"Video son kare eklenerek uzatıldı: {extended_video}")
                    video_path = extended_video
            except Exception as extend_error:
                print(f"Video uzatma hatası: {str(extend_error)}")
            
            # Ses ve videoya uygun bir encoder seç, daha yüksek ses kalitesi
            audio_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -i "{os.path.abspath(merged_audio)}" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -af "aresample=async=1000" "{os.path.abspath(audio_video)}"'
            
            try:
                subprocess.run(audio_cmd, shell=True, check=True)
                
                # Başarılı mı kontrol et
                if os.path.exists(audio_video) and os.path.getsize(audio_video) > 0:
                    print(f"Ses başarıyla eklendi: {audio_video}")
                else:
                    raise Exception("Ses eklenmiş video oluşturulamadı")
            except Exception as e:
                print(f"Ses ekleme hatası: {str(e)}")
                # Alternatif yöntem dene
                try:
                    alt_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -i "{os.path.abspath(merged_audio)}" -c:v copy -c:a aac -strict experimental "{os.path.abspath(audio_video)}"'
                    subprocess.run(alt_cmd, shell=True, check=True)
                    
                    if os.path.exists(audio_video) and os.path.getsize(audio_video) > 0:
                        print("Alternatif ses ekleme başarılı")
                    else:
                        # Hata durumunda orijinal videoyu kopyala
                        shutil.copy2(video_path, audio_video)
                except Exception as alt_error:
                    print(f"Alternatif ses ekleme hatası: {str(alt_error)}")
                    # Hata durumunda orijinal videoyu kopyala
                    shutil.copy2(video_path, audio_video)
        else:
            # Ses birleştirme başarısız olmuşsa orijinal videoyu kopyala
            print("Ses birleştirme başarısız, orijinal video kullanılıyor...")
            shutil.copy2(video_path, audio_video)
        
        # Geçici dosyaları temizle
        try:
            if os.path.exists(merged_audio):
                os.remove(merged_audio)
            if os.path.exists(os.path.join(project_folder, "concat_list.txt")):
                os.remove(os.path.join(project_folder, "concat_list.txt"))
            if os.path.exists(os.path.join(project_folder, "adjusted_video.mp4")):
                os.remove(os.path.join(project_folder, "adjusted_video.mp4"))
            if os.path.exists(os.path.join(project_folder, "trimmed_video.mp4")):
                os.remove(os.path.join(project_folder, "trimmed_video.mp4"))
            if os.path.exists(os.path.join(project_folder, "extended_video.mp4")):
                os.remove(os.path.join(project_folder, "extended_video.mp4"))
        except Exception as e:
            print(f"Geçici dosya silme hatası: {str(e)}")
        
        return audio_video
        
    except Exception as e:
        print(f"Ses birleştirme genel hatası: {str(e)}")
        # Hata durumunda orijinal videoyu kopyala
        try:
            audio_video = os.path.join(project_folder, "video_with_audio.mp4")
            shutil.copy2(video_path, audio_video)
            return audio_video
        except Exception as copy_error:
            print(f"Dosya kopyalama hatası: {str(copy_error)}")
            # Son çare - boş dosya
            with open(os.path.join(project_folder, "video_with_audio.mp4"), 'wb') as f:
                f.write(b'')
            return os.path.join(project_folder, "video_with_audio.mp4")
