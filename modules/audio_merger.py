#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
from typing import List
import tempfile
import shutil
import json
import sys
import platform

def detect_hardware_acceleration():
    """
    Sistemde mevcut donanım hızlandırma özelliklerini tespit eder
    
    Returns:
        dict: Mevcut donanım hızlandırma özellikleri ve uygun FFmpeg parametreleri
    """
    hw_accel = {
        "available": False,
        "type": None,
        "params": []
    }
    
    # Windows için NVIDIA GPU tespiti
    if platform.system() == "Windows":
        try:
            # NVIDIA GPU kontrolü
            nvidia_check = subprocess.run("nvidia-smi", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if nvidia_check.returncode == 0:
                hw_accel["available"] = True
                hw_accel["type"] = "nvidia"
                hw_accel["params"] = ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
                print("NVIDIA GPU tespit edildi, CUDA hızlandırma kullanılacak")
                return hw_accel
                
            # Intel GPU kontrolü
            if os.path.exists("C:\\Program Files\\Intel\\Media SDK"):
                hw_accel["available"] = True
                hw_accel["type"] = "intel"
                hw_accel["params"] = ["-hwaccel", "qsv"]
                print("Intel GPU tespit edildi, QSV hızlandırma kullanılacak")
                return hw_accel
        except:
            pass
    
    # Linux için GPU tespiti
    elif platform.system() == "Linux":
        try:
            # NVIDIA GPU kontrolü
            nvidia_check = subprocess.run("which nvidia-smi", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if nvidia_check.returncode == 0:
                hw_accel["available"] = True
                hw_accel["type"] = "nvidia"
                hw_accel["params"] = ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
                print("NVIDIA GPU tespit edildi, CUDA hızlandırma kullanılacak")
                return hw_accel
                
            # VAAPI kontrolü (AMD ve Intel için)
            vaapi_check = subprocess.run("vainfo", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if vaapi_check.returncode == 0:
                hw_accel["available"] = True
                hw_accel["type"] = "vaapi"
                hw_accel["params"] = ["-hwaccel", "vaapi", "-vaapi_device", "/dev/dri/renderD128"]
                print("VAAPI destekli GPU tespit edildi, VAAPI hızlandırma kullanılacak")
                return hw_accel
        except:
            pass
    
    # macOS için Metal kontrolü
    elif platform.system() == "Darwin":
        hw_accel["available"] = True
        hw_accel["type"] = "videotoolbox"
        hw_accel["params"] = ["-hwaccel", "videotoolbox"]
        print("macOS videotoolbox hızlandırma etkinleştirildi")
        return hw_accel
    
    print("Donanım hızlandırma tespit edilemedi, yazılım kodlama kullanılacak")
    return hw_accel

def get_optimized_ffmpeg_params(input_path, output_path, hw_accel):
    """
    En uygun FFmpeg parametrelerini getirir
    
    Args:
        input_path (str): Giriş dosyasının yolu
        output_path (str): Çıkış dosyasının yolu
        hw_accel (dict): Donanım hızlandırma bilgileri
        
    Returns:
        list: FFmpeg komut satırı parametreleri
    """
    # Temel parametreler
    params = ["-y"]  # Mevcut dosyanın üzerine yaz
    
    # Donanım hızlandırma parametreleri
    if hw_accel["available"]:
        params.extend(hw_accel["params"])
    
    # Giriş dosyası
    params.extend(["-i", input_path])
    
    # Video kodlayıcı ve optimizasyonlar
    if hw_accel["available"]:
        if hw_accel["type"] == "nvidia":
            params.extend([
                "-c:v", "h264_nvenc",
                "-preset", "p4",
                "-tune", "hq",
                "-b:v", "5M",
                "-maxrate", "5M",
                "-bufsize", "5M"
            ])
        elif hw_accel["type"] == "intel":
            params.extend([
                "-c:v", "h264_qsv",
                "-preset", "faster",
                "-b:v", "5M"
            ])
        elif hw_accel["type"] == "vaapi":
            params.extend([
                "-vf", "format=nv12,hwupload",
                "-c:v", "h264_vaapi",
                "-b:v", "5M"
            ])
        elif hw_accel["type"] == "videotoolbox":
            params.extend([
                "-c:v", "h264_videotoolbox",
                "-b:v", "5M",
                "-maxrate", "5M",
                "-bufsize", "5M"
            ])
    else:
        # Yazılım kodlama - optimize edilmiş
        params.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-profile:v", "high",
            "-pix_fmt", "yuv420p"
        ])
    
    # Ses kodlayıcı
    params.extend([
        "-c:a", "aac",
        "-b:a", "192k"
    ])
    
    # Diğer hızlandırma parametreleri
    params.extend([
        "-movflags", "+faststart",   # Web'de daha hızlı oynatma
        "-threads", str(min(os.cpu_count(), 16))  # Thread sayısını optimize et
    ])
    
    # Çıkış dosyası
    params.append(output_path)
    
    return params

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
    
    # Donanım hızlandırma tespiti
    hw_accel = detect_hardware_acceleration()
    
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
            if audio_duration > video_duration * 1.05:  # Ses %5'den fazla uzunsa (daha hassas)
                print(f"Uyarı: Ses süresi video süresinden %{((audio_duration / video_duration) - 1) * 100:.1f} daha uzun")
                print("Video sesi uyumlu hale getirmek için düzenlenecek...")
                
                # Videoyu yavaşlat ve ses süresine uygun hale getir
                speed_factor = video_duration / audio_duration
                adjusted_video = os.path.join(project_folder, "adjusted_video.mp4")
                
                # Donanım hızlandırma ile video işleme
                base_params = [ffmpeg_path, "-i", os.path.abspath(video_path)]
                
                if hw_accel["available"]:
                    base_params.extend(hw_accel["params"])
                
                # Hız ayarı için filter
                filter_params = ["-filter:v", f"setpts={1/speed_factor}*PTS"]
                
                # Codec seçimi
                if hw_accel["available"] and hw_accel["type"] == "nvidia":
                    codec_params = ["-c:v", "h264_nvenc", "-preset", "p4"]
                else:
                    codec_params = ["-c:v", "libx264", "-preset", "fast", "-crf", "22"]
                
                # Diğer parametreler
                output_params = ["-pix_fmt", "yuv420p", os.path.abspath(adjusted_video)]
                
                # Tam komutu oluştur
                adjust_cmd_parts = base_params + filter_params + codec_params + output_params
                adjust_cmd = " ".join([f'"{p}"' if " " in str(p) else str(p) for p in adjust_cmd_parts])
                
                try:
                    subprocess.run(adjust_cmd, shell=True, check=True)
                    if os.path.exists(adjusted_video) and os.path.getsize(adjusted_video) > 0:
                        video_path = adjusted_video
                        print(f"Video sese uygun şekilde yavaşlatıldı: {adjusted_video}")
                except Exception as adjust_error:
                    print(f"Video düzenleme hatası: {str(adjust_error)}")
        
            elif video_duration > audio_duration * 1.1:  # Video %10'dan fazla uzunsa (daha hassas)
                print(f"Uyarı: Video süresi ses süresinden %{((video_duration / audio_duration) - 1) * 100:.1f} daha uzun")
                print("Video sese uyumlu hale getirmek için kırpılacak...")
                
                # Video süresini sese uygun şekilde kırp
                trimmed_video = os.path.join(project_folder, "trimmed_video.mp4")
                
                # Optimize edilmiş kırpma komutu
                trim_cmd_parts = [
                    ffmpeg_path,
                    "-y",
                    "-i", os.path.abspath(video_path),
                    "-t", str(audio_duration * 1.05),
                    "-c:v", "copy",  # Yeniden kodlama yapmadan kopyala
                    os.path.abspath(trimmed_video)
                ]
                
                trim_cmd = " ".join([f'"{p}"' if " " in str(p) else str(p) for p in trim_cmd_parts])
                
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
            
            # Sesleri birleştir - optimizasyon: -c copy kullanarak yeniden kodlama yapmadan birleştir
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
            
            # Optimize edilmiş ses ekleme komutu
            audio_video_params = get_optimized_ffmpeg_params(
                os.path.abspath(video_path),
                os.path.abspath(audio_video),
                hw_accel
            )
            
            # Parametre listesini oluştur
            ffmpeg_cmd_parts = [ffmpeg_path]
            
            # Giriş dosyalarını ekle
            ffmpeg_cmd_parts.extend(["-i", os.path.abspath(video_path), "-i", os.path.abspath(merged_audio)])
            
            # Map parametreleri
            ffmpeg_cmd_parts.extend(["-map", "0:v", "-map", "1:a"])
            
            # -shortest parametresi - en kısa olanın uzunluğunu kullan
            ffmpeg_cmd_parts.append("-shortest")
            
            # Ses senkronizasyonu için
            ffmpeg_cmd_parts.extend(["-af", "aresample=async=1000"])
            
            # Donanım hızlandırma
            if hw_accel["available"]:
                if hw_accel["type"] == "nvidia":
                    ffmpeg_cmd_parts.extend(["-c:v", "h264_nvenc", "-preset", "p4"])
                elif hw_accel["type"] == "intel":
                    ffmpeg_cmd_parts.extend(["-c:v", "h264_qsv"])
                elif hw_accel["type"] == "vaapi":
                    ffmpeg_cmd_parts.extend(["-vf", "format=nv12,hwupload", "-c:v", "h264_vaapi"])
                elif hw_accel["type"] == "videotoolbox":
                    ffmpeg_cmd_parts.extend(["-c:v", "h264_videotoolbox"])
            else:
                # Video kodlayıcı - copy kullan (yeniden kodlama yapmadan)
                ffmpeg_cmd_parts.extend(["-c:v", "copy"])
            
            # Ses kodlayıcı
            ffmpeg_cmd_parts.extend(["-c:a", "aac", "-b:a", "256k"])
            
            # Çıkış dosyası
            ffmpeg_cmd_parts.append(os.path.abspath(audio_video))
            
            # Komut dizesini oluştur
            audio_cmd = " ".join([f'"{p}"' if " " in str(p) else str(p) for p in ffmpeg_cmd_parts])
            
            try:
                subprocess.run(audio_cmd, shell=True, check=True)
                
                # Başarılı mı kontrol et
                if os.path.exists(audio_video) and os.path.getsize(audio_video) > 0:
                    print(f"Ses başarıyla eklendi: {audio_video}")
                else:
                    raise Exception("Ses eklenmiş video oluşturulamadı")
            except Exception as e:
                print(f"Ses ekleme hatası: {str(e)}")
                # Alternatif yöntem dene - daha basit parametre seti kullanarak
                try:
                    alt_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -i "{os.path.abspath(merged_audio)}" -c:v copy -c:a aac -shortest "{os.path.abspath(audio_video)}"'
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
        except Exception as e:
            print(f"Geçici dosya temizleme hatası: {str(e)}")
        
        return audio_video
    
    except Exception as e:
        print(f"Audio merger genel hatası: {str(e)}")
        # Hata durumunda orijinal videoyu kopyala
        audio_video = os.path.join(project_folder, "video_with_audio.mp4")
        try:
            shutil.copy2(video_path, audio_video)
        except:
            # En son çare, boş bir dosya oluştur
            with open(audio_video, 'wb') as f:
                f.write(b'')
        return audio_video
