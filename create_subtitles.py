#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
import subprocess
import shutil
from datetime import datetime

def format_srt_time(seconds):
    """Convert seconds to SRT timestamp format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    milliseconds = int((secs - int(secs)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{milliseconds:03d}"

def main():
    # Proje klasörü ve video yolu
    project_folder = r"C:\Users\pc\Desktop\MMoto\output\video_2025-04-10_01-17-27"
    video_path = os.path.join(project_folder, "video_with_audio.mp4")
    output_path = os.path.join(project_folder, "video_with_subtitles.mp4")
    ffmpeg_path = r"C:\Users\pc\Desktop\MMoto\bin\bin\ffmpeg.exe"
    
    # Log dosyası oluştur
    log_path = os.path.join(project_folder, "subtitle_creation.log")
    
    with open(log_path, "w", encoding="utf-8") as log:
        log.write(f"Starting subtitle creation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # JSON dosyasını bul
        json_path = os.path.join(project_folder, "tts_audio", "full_timing.json")
        if not os.path.exists(json_path):
            log.write(f"JSON file not found at {json_path}\n")
            return
        
        log.write(f"Found timing JSON at {json_path}\n")
        
        # JSON'dan zamanlamaları yükle
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            log.write(f"Successfully loaded JSON with keys: {list(data.keys())}\n")
        except Exception as e:
            log.write(f"Error loading JSON: {str(e)}\n")
            return
        
        # Kelime zamanlamalarını çıkar - segments formatını dene
        words = []
        if "segments" in data and isinstance(data["segments"], list):
            for segment in data["segments"]:
                if "words" in segment and isinstance(segment["words"], list):
                    segment_words = [w for w in segment["words"] 
                                    if "word" in w and "start" in w and "end" in w]
                    words.extend(segment_words)
        
        # Düz words array formatını dene
        elif "words" in data and isinstance(data["words"], list):
            words = [w for w in data["words"] if "word" in w and "start" in w and "end" in w]
        
        log.write(f"Found {len(words)} words with timing\n")
        
        if not words:
            log.write("No word timings found in JSON\n")
            return
        
        # SRT dosyası oluştur
        srt_path = os.path.join(project_folder, "word_by_word.srt")
        with open(srt_path, "w", encoding="utf-8") as srt_file:
            for i, word in enumerate(words, 1):
                # SRT formatına dönüştür
                start = format_srt_time(word["start"])
                end = format_srt_time(word["end"])
                text = word["word"].strip()
                
                # Büyük fontlu, beyaz yazı, siyah arka plan
                styled_text = f'<font size="36" color="white"><b>{text}</b></font>'
                
                # SRT girişini yaz
                srt_file.write(f"{i}\n")
                srt_file.write(f"{start} --> {end}\n")
                srt_file.write(f"{styled_text}\n\n")
        
        log.write(f"Created SRT file with {len(words)} word entries at {srt_path}\n")
        
        # FFmpeg ile altyazıları videoya ekle - basit shell yöntemi kullan
        srt_filename = os.path.basename(srt_path)
        cmd = f'"{ffmpeg_path}" -y -i "{video_path}" -vf "subtitles={srt_filename}" -c:v libx264 -c:a copy "{output_path}"'
        log.write(f"Running FFmpeg command: {cmd}\n")
        
        # Komut çalıştırılacak dizini değiştir
        try:
            process = subprocess.Popen(
                cmd,
                shell=True,
                cwd=project_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            
            log.write(f"FFmpeg stdout: {stdout.decode('utf-8', errors='ignore')}\n")
            log.write(f"FFmpeg stderr: {stderr.decode('utf-8', errors='ignore')}\n")
            
            if process.returncode == 0 and os.path.exists(output_path):
                log.write(f"Success! Created subtitled video at {output_path}\n")
            else:
                log.write("FFmpeg command failed\n")
        except Exception as e:
            log.write(f"Error running FFmpeg: {str(e)}\n")

if __name__ == "__main__":
    main() 