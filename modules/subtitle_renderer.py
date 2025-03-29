#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
from typing import List, Dict, Any, Tuple
import tempfile
import shutil
import json
import textwrap
import re
from datetime import datetime

# PIL modülünü dahil et (kurulu değilse uyarı ver)
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Uyarı: PIL kütüphanesi bulunamadı. PNG altyazı yöntemi kullanılamayacak.")

def create_word_level_ass(sentences: List[str], timings: List[Dict[str, Any]], output_path: str) -> bool:
    """
    Kelime seviyesinde ASS/SSA altyazı dosyası oluşturur
    
    Args:
        sentences (List[str]): Altyazı cümleleri (referans için)
        timings (List[Dict[str, Any]]): Kelime zamanlamaları
        output_path (str): Çıktı ASS dosyasının yolu
    
    Returns:
        bool: Başarılı ise True, değilse False
    """
    try:
        # Font dosyasının tam yolunu al
        font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts", "Anton-Regular.ttf")
        font_name = "Anton-Regular"
        
        # Font dosyasının varlığını kontrol et
        if not os.path.exists(font_path):
            print(f"Uyarı: Anton-Regular.ttf bulunamadı: {font_path}")
            font_name = "Arial" # Yedek font
        
        # ASS dosyası başlık bölümü
        ass_header = f"""[Script Info]
Title: Kelime Bazlı Dinamik Altyazılar
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},60,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,6,0,2,10,10,138,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        # ASS dosyasını oluştur
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_header)
            
            # Tüm kelimeleri topla
            all_words = []
            cumulative_time = 0.0
            
            # Ses dosyalarının gerçek sürelerini hesapla
            audio_durations = []
            for timing_data in timings:
                if "words" in timing_data and timing_data["words"] and len(timing_data["words"]) > 0:
                    last_word = timing_data["words"][-1]
                    if "end" in last_word:
                        audio_durations.append(last_word["end"])
                    else:
                        audio_durations.append(0.0)
                else:
                    audio_durations.append(0.0)
            
            # Her ses dosyası için kelimeleri ekle
            for i, timing_data in enumerate(timings):
                if "words" in timing_data and timing_data["words"]:
                    for word_info in timing_data["words"]:
                        if "word" in word_info and "start" in word_info and "end" in word_info:
                            # Kelime bilgisini kopyala ve kümülatif zamanı ekle
                            adjusted_word = {
                                "word": word_info["word"].strip(),
                                "start": word_info["start"] + cumulative_time,
                                "end": word_info["end"] + cumulative_time
                            }
                            all_words.append(adjusted_word)
                    
                    # Bir sonraki ses dosyası için kümülatif zamanı güncelle
                    # Gerçek ses süresini kullan ve daha az boşluk bırak
                    if i < len(audio_durations):
                        cumulative_time += audio_durations[i] + 0.05  # 0.05 saniye boşluk (daha az)
            
            # Her kelime için ASS olayı ekle
            for i, word in enumerate(all_words):
                start_time = format_ass_time(word["start"])
                
                # Her kelimenin kendi zamanlamasını kullan, çok küçük bir boşluk bırak
                # Bu, senkronizasyonu daha doğru hale getirir
                if i < len(all_words) - 1:
                    # Bir sonraki kelimeyle çakışmayı önle, ama çok küçük bir boşluk bırak
                    next_start = all_words[i+1]["start"]
                    # Kelimenin kendi bitiş zamanını kullan, ama bir sonraki kelimenin başlangıcını geçme
                    end_time = format_ass_time(min(word["end"] + 0.02, next_start - 0.01))
                else:
                    # Son kelime için normal bitiş zamanı + küçük bir boşluk
                    end_time = format_ass_time(word["end"] + 0.02)
                
                text = word["word"]
                
                # Özel karakterleri escape et
                text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
                
                # ASS olayı ekle - alt-ortada göster (alignment=7)
                f.write(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n")
        
        return True
    except Exception as e:
        print(f"ASS dosyası oluşturma hatası: {str(e)}")
        return False

def render_subtitles(video_path: str, sentences: List[str], font_path: str, project_folder: str) -> str:
    """
    Videoya altyazı ekler
    
    Args:
        video_path (str): İşlenecek video dosyasının yolu
        sentences (List[str]): Eklenecek altyazılar
        font_path (str): Kullanılacak font dosyasının yolu
        project_folder (str): Proje klasörünün yolu
    
    Returns:
        str: Altyazı eklenmiş video dosyasının yolu
    """
    # Altyazı bilgilerini kaydedecek dosya
    subtitle_log_path = os.path.join(project_folder, "subtitle_log.txt")
    
    # FFmpeg yolunu config.json'dan al
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    ffmpeg_path = "ffmpeg"  # Varsayılan değer
    ffprobe_path = "ffprobe"  # Varsayılan değer
    
    with open(subtitle_log_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"=== Altyazı İşlemi Başlangıcı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        log_file.write(f"Video yolu: {video_path}\n")
        log_file.write(f"Font yolu: {font_path}\n")
        log_file.write(f"Altyazı sayısı: {len(sentences)}\n\n")
        log_file.write("--- Altyazı İçerikleri ---\n")
        for i, sentence in enumerate(sentences):
            log_file.write(f"Altyazı {i+1}: {sentence}\n")
        log_file.write("\n")
    
    # Basit bir HTML önizleme dosyası oluştur
    html_preview = os.path.join(project_folder, "subtitle_preview.html")
    with open(html_preview, 'w', encoding='utf-8') as html_file:
        html_file.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Altyazı Önizleme</title>
    <style>
        body { background-color: #000; color: #fff; font-family: Arial, sans-serif; text-align: center; }
        .container { display: flex; flex-direction: column; height: 100vh; align-items: center; justify-content: center; }
        .subtitle-box { 
            width: 80%; 
            max-width: 400px; 
            background-color: rgba(0,0,0,0.8); 
            padding: 20px; 
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(255,255,255,0.2);
            margin-bottom: 20px;
        }
        .subtitle { 
            font-size: 18px; 
            font-weight: bold; 
            margin: 0;
            padding: 10px;
            text-shadow: 2px 2px 2px rgba(0,0,0,0.8);
        }
        h1 { margin-bottom: 30px; }
        .note { color: #aaa; font-size: 14px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Altyazı Önizleme</h1>
""")
        
        # Altyazıları ekle
        for i, sentence in enumerate(sentences):
            # Cümleyi daha anlamlı bir şekilde böl
            sentence = sentence.strip()
            
            # Noktalama işaretlerini kontrol et (virgül, noktalı virgül, iki nokta)
            punctuation_marks = [',', ';', ':']
            best_split_point = -1
            
            # Cümlenin ortasına yakın bir noktalama işareti bul
            sentence_length = len(sentence)
            mid_point = sentence_length // 2
            
            # Ortaya en yakın noktalama işaretini bul
            min_distance = sentence_length
            for idx, char in enumerate(sentence):
                if char in punctuation_marks:
                    distance = abs(idx - mid_point)
                    if distance < min_distance:
                        min_distance = distance
                        best_split_point = idx + 1  # Noktalama işaretinden sonra böl
            
            # Eğer uygun noktalama işareti bulunamazsa, en yakın boşluğu bul
            if best_split_point == -1:
                min_distance = sentence_length
                for idx, char in enumerate(sentence):
                    if char == ' ':
                        distance = abs(idx - mid_point)
                        if distance < min_distance:
                            min_distance = distance
                            best_split_point = idx
            
            # Hala bölme noktası bulunamadıysa, ortadan böl
            if best_split_point == -1:
                best_split_point = mid_point
            
            first_half = sentence[:best_split_point].strip()
            second_half = sentence[best_split_point:].strip()
            
            html_file.write('        <div class="subtitle-box">\n')
            html_file.write(f'            <p class="subtitle">Cümle {i+1} - İlk Yarı: {first_half}</p>\n')
            html_file.write('        </div>\n')
            
            html_file.write('        <div class="subtitle-box">\n')
            html_file.write(f'            <p class="subtitle">Cümle {i+1} - İkinci Yarı: {second_half}</p>\n')
            html_file.write('        </div>\n')
        
        html_file.write("""        <p class="note">Not: Bu sayfa sadece altyazıların önizlemesi içindir. 
        Asıl videoyu görüntülemez.</p>
</div>
</body>
</html>""")
    
    # Config dosyasından FFmpeg ve FFprobe yollarını al
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                
                # Kök dizini hesapla
                root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                
                # FFmpeg yolu
                if "ffmpeg_path" in config:
                    ffmpeg_path = os.path.join(root_dir, config["ffmpeg_path"])
                    with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                        log_file.write(f"FFmpeg yolu: {ffmpeg_path}\n")
                
                # FFprobe yolu
                if "ffprobe_path" in config:
                    ffprobe_path = os.path.join(root_dir, config["ffprobe_path"])
                    with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                        log_file.write(f"FFprobe yolu: {ffprobe_path}\n")
        except Exception as e:
            print(f"Config dosyası okuma hatası: {str(e)}")
            with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"Config dosyası okuma hatası: {str(e)}\n")
    
    if not os.path.exists(video_path):
        print(f"Hata: Video dosyası bulunamadı: {video_path}")
        # Boş bir çıktı dosyası oluştur
        subtitled_video = os.path.join(project_folder, "subtitled_video.mp4")
        if os.path.exists(video_path):
            shutil.copy2(video_path, subtitled_video)
        else:
            with open(subtitled_video, 'wb') as f:
                f.write(b'')
        return subtitled_video
    
    # Font dosyasını kontrol et
    if not os.path.exists(font_path):
        # Font yolunu daha güvenli bir şekilde hesapla
        font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts", "Montserrat-Bold.ttf")
        
        if not os.path.exists(font_path):
            print("Uyarı: Font dosyası bulunamadı, font kullanılmayacak")
            font_path = ""
    
    # Font yolunu göreli değil mutlak yol olarak kullan
    if font_path:
        font_path = os.path.abspath(font_path)
        with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"Mutlak font yolu: {font_path}\n")
    
    try:
        # Altyazılı video dosyasının yolu
        subtitled_video = os.path.join(project_folder, "subtitled_video.mp4")
        
        # Video süresini öğren
        duration_cmd = f'"{ffprobe_path}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{os.path.abspath(video_path)}"'
        duration = 0
        try:
            result = subprocess.run(duration_cmd, shell=True, capture_output=True, text=True)
            duration = float(result.stdout.strip())
            print(f"Video süresi: {duration} saniye")
        except Exception as e:
            print(f"Video süresi alınamadı: {str(e)}")
            duration = 30  # Varsayılan değer

        # Ses dosyalarının sürelerini al - her ses dosyası bir altyazı cümlesi içindir
        audio_durations = []
        audio_total_duration = 0
        
        # TTS ses dosyalarını kontrol et
        tts_audio_dir = os.path.join(project_folder, "tts_audio")
        if os.path.exists(tts_audio_dir):
            # Ses dosyalarını listele
            audio_files = []
            for file in os.listdir(tts_audio_dir):
                if file.endswith('.mp3') or file.endswith('.wav'):
                    audio_files.append(os.path.join(tts_audio_dir, file))
            
            # Ses dosyalarını sırala (audio_01.mp3, audio_02.mp3, ... şeklinde)
            audio_files.sort()
            
            with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"Bulunan ses dosyaları: {len(audio_files)}\n")
                for i, audio_file in enumerate(audio_files):
                    log_file.write(f"  {i+1}. {os.path.basename(audio_file)}\n")
            
            # Her bir ses dosyasının süresini al
            for i, audio_file in enumerate(audio_files):
                if os.path.exists(audio_file):
                    try:
                        # Ses dosyasının süresini al
                        audio_duration_cmd = f'"{ffprobe_path}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{os.path.abspath(audio_file)}"'
                        audio_result = subprocess.run(audio_duration_cmd, shell=True, capture_output=True, text=True)
                        file_duration = float(audio_result.stdout.strip())
                        audio_durations.append(file_duration)
                        audio_total_duration += file_duration
                        with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                            log_file.write(f"Ses dosyası {os.path.basename(audio_file)} süresi: {file_duration:.2f} saniye\n")
                    except Exception as e:
                        # Süre alınamazsa cümle sayısına göre yaklaşık bir süre hesapla
                        estimated_duration = duration / len(sentences)
                        audio_durations.append(estimated_duration)
                        audio_total_duration += estimated_duration
                        with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                            log_file.write(f"Ses dosyası {os.path.basename(audio_file)} süre alınamadı: {str(e)}, tahmin edildi: {estimated_duration:.2f} saniye\n")
            
            # Ses dosyası sayısı ile cümle sayısı farklı ise ayarlama yap
            if len(audio_durations) != len(sentences):
                with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                    log_file.write(f"UYARI: Ses dosyası sayısı ({len(audio_durations)}) ve cümle sayısı ({len(sentences)}) eşleşmiyor!\n")
                
                # Ses dosyası sayısı daha az ise, eksik olanları tahmin et
                if len(audio_durations) < len(sentences):
                    remaining_duration = max(0, duration - audio_total_duration)
                    remaining_sentences = len(sentences) - len(audio_durations)
                    estimated_per_sentence = remaining_duration / max(1, remaining_sentences)
                    
                    for i in range(remaining_sentences):
                        audio_durations.append(estimated_per_sentence)
                        audio_total_duration += estimated_per_sentence
                        with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                            log_file.write(f"Eksik ses dosyası için tahmin: {estimated_per_sentence:.2f} saniye\n")
                
                # Ses dosyası sayısı daha fazla ise, fazla olanları yok say
                elif len(audio_durations) > len(sentences):
                    audio_durations = audio_durations[:len(sentences)]
                    audio_total_duration = sum(audio_durations)
                    with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                        log_file.write(f"Fazla ses dosyaları yok sayıldı. Toplam süre: {audio_total_duration:.2f} saniye\n")
        else:
            # TTS klasörü yoksa, cümle sayısına göre eşit süre böl
            for i in range(len(sentences)):
                estimated_duration = duration / len(sentences)
                audio_durations.append(estimated_duration)
                audio_total_duration += estimated_duration
            
            with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"TTS klasörü bulunamadı, her cümle için tahmini süre: {duration/len(sentences):.2f} saniye\n")
        
        # Kelime zamanlamalarını yükle
        word_timings = load_word_timings(project_folder)
        
        # Altyazı dosyası yolları
        srt_path = os.path.join(project_folder, "subtitles.srt")
        ass_path = os.path.join(project_folder, "subtitles.ass")
        
        # Kelime zamanlamaları varsa, kelime seviyesinde ASS oluştur (yeni yöntem)
        if word_timings:
            with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"Kelime zamanlamaları bulundu: {len(word_timings)} dosya\n")
            
            # Anton-Regular.ttf fontunu kullan
            anton_font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts", "Anton-Regular.ttf")
            if os.path.exists(anton_font_path):
                font_path = anton_font_path
                with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                    log_file.write(f"Anton-Regular.ttf fontu kullanılacak: {font_path}\n")
            
            # Kelime seviyesinde ASS oluştur
            if create_word_level_ass(sentences, word_timings, ass_path):
                with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                    log_file.write(f"Kelime seviyesinde ASS dosyası oluşturuldu: {ass_path}\n\n")
                
                # ASS dosyasını kullanarak altyazı ekle
                ass_subtitle_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -vf "ass={ass_path.replace("\\", "/")}" -c:a copy "{os.path.abspath(subtitled_video)}"'
                
                with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                    log_file.write("--- ASS Altyazı Komutu ---\n")
                    log_file.write(f"{ass_subtitle_cmd}\n\n")
                
                print("ASS altyazı komutu çalıştırılıyor...")
                
                try:
                    ass_result = subprocess.run(ass_subtitle_cmd, shell=True, capture_output=True, text=True)
                    with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                        log_file.write("ASS komut çıktısı:\n")
                        log_file.write(f"STDOUT: {ass_result.stdout}\n")
                        log_file.write(f"STDERR: {ass_result.stderr}\n\n")
                    
                    # Başarılı olup olmadığını kontrol et
                    if os.path.exists(subtitled_video) and os.path.getsize(subtitled_video) > 0:
                        print(f"ASS altyazılar başarıyla eklendi: {subtitled_video}")
                        with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                            log_file.write("ASS altyazı ekleme başarılı!\n\n")
                        return subtitled_video
                    else:
                        # ASS başarısız olduysa SRT yöntemini dene
                        with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                            log_file.write("ASS altyazı ekleme başarısız oldu, SRT yöntemi deneniyor...\n\n")
                except Exception as e:
                    print(f"ASS altyazı hatası: {str(e)}")
                    with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                        log_file.write(f"ASS altyazı hatası: {str(e)}\n")
                        log_file.write("SRT yöntemi deneniyor...\n\n")
            else:
                # ASS oluşturma başarısız olduysa SRT yöntemini dene
                with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                    log_file.write("ASS dosyası oluşturma başarısız oldu, SRT yöntemi deneniyor...\n\n")
            
            # ASS başarısız olduysa veya oluşturulamadıysa, SRT ile devam et
            # Kelime seviyesinde SRT oluştur
            create_word_level_srt(sentences, word_timings, srt_path)
            
            with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"Kelime seviyesinde SRT dosyası oluşturuldu: {srt_path}\n\n")
        else:
            # Kelime zamanlamaları yoksa, eski yöntemi kullan (cümleleri ikiye böl)
            with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                log_file.write("Kelime zamanlamaları bulunamadı, cümleleri ikiye bölerek SRT oluşturuluyor...\n")
            
            with open(srt_path, 'w', encoding='utf-8') as srt_file:
                subtitle_index = 1
                current_time = 0
                
                for i, sentence in enumerate(sentences):
                    if i < len(audio_durations):
                        total_duration = audio_durations[i]
                        
                        # Cümlenin ilk yarısı için zaman aralığı
                        first_half_start = current_time
                        first_half_end = current_time + (total_duration / 2)
                        
                        # Cümlenin ikinci yarısı için zaman aralığı
                        second_half_start = first_half_end
                        second_half_end = current_time + total_duration
                        
                        # Bir sonraki cümle için başlangıç zamanını güncelle
                        current_time = second_half_end
                        
                        # Küçük bir boşluk ekleyelim
                        if i < len(sentences) - 1:
                            current_time += 0.1
                    else:
                        # Eğer ses dosyası yoksa varsayılan hesaplama kullan
                        total_duration = duration / max(1, len(sentences))
                        first_half_start = i * total_duration
                        first_half_end = first_half_start + (total_duration / 2)
                        second_half_start = first_half_end
                        second_half_end = (i + 1) * total_duration
                    
                    # Cümleyi daha anlamlı bir şekilde böl
                    sentence = sentence.strip()
                    
                    # Noktalama işaretlerini kontrol et (virgül, noktalı virgül, iki nokta)
                    punctuation_marks = [',', ';', ':']
                    best_split_point = -1
                    
                    # Cümlenin ortasına yakın bir noktalama işareti bul
                    sentence_length = len(sentence)
                    mid_point = sentence_length // 2
                    
                    # Ortaya en yakın noktalama işaretini bul
                    min_distance = sentence_length
                    for idx, char in enumerate(sentence):
                        if char in punctuation_marks:
                            distance = abs(idx - mid_point)
                            if distance < min_distance:
                                min_distance = distance
                                best_split_point = idx + 1  # Noktalama işaretinden sonra böl
                    
                    # Eğer uygun noktalama işareti bulunamazsa, en yakın boşluğu bul
                    if best_split_point == -1:
                        min_distance = sentence_length
                        for idx, char in enumerate(sentence):
                            if char == ' ':
                                distance = abs(idx - mid_point)
                                if distance < min_distance:
                                    min_distance = distance
                                    best_split_point = idx
                    
                    # Hala bölme noktası bulunamadıysa, ortadan böl
                    if best_split_point == -1:
                        best_split_point = mid_point
                    
                    first_half = sentence[:best_split_point].strip()
                    second_half = sentence[best_split_point:].strip()
                    
                    # Log dosyasına bölme bilgisini yaz
                    with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                        log_file.write(f"Cümle {i+1} bölme noktası: {best_split_point}/{sentence_length}\n")
                        log_file.write(f"  İlk yarı: {first_half}\n")
                        log_file.write(f"  İkinci yarı: {second_half}\n")
                    
                    # İlk yarı için SRT girişi ekle
                    srt_file.write(f"{subtitle_index}\n")
                    srt_file.write(f"{format_srt_time(first_half_start)} --> {format_srt_time(first_half_end)}\n")
                    srt_file.write(f"{first_half}\n\n")
                    subtitle_index += 1
                    
                    # İkinci yarı için SRT girişi ekle
                    srt_file.write(f"{subtitle_index}\n")
                    srt_file.write(f"{format_srt_time(second_half_start)} --> {format_srt_time(second_half_end)}\n")
                    srt_file.write(f"{second_half}\n\n")
                    subtitle_index += 1
            
            with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"SRT dosyası oluşturuldu (cümleler ikiye bölündü): {srt_path}\n\n")
        
        # SRT dosyasını kullanarak altyazı ekle (ASS başarısız olduysa veya kelime zamanlamaları yoksa)
        srt_subtitle_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -vf "subtitles={srt_path.replace("\\", "/")}" -c:a copy "{os.path.abspath(subtitled_video)}"'
        
        with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
            log_file.write("--- SRT Altyazı Komutu ---\n")
            log_file.write(f"{srt_subtitle_cmd}\n\n")
        
        print("SRT altyazı komutu çalıştırılıyor...")
        
        try:
            srt_result = subprocess.run(srt_subtitle_cmd, shell=True, capture_output=True, text=True)
            with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                log_file.write("SRT komut çıktısı:\n")
                log_file.write(f"STDOUT: {srt_result.stdout}\n")
                log_file.write(f"STDERR: {srt_result.stderr}\n\n")
            
            # Başarılı olup olmadığını kontrol et
            if os.path.exists(subtitled_video) and os.path.getsize(subtitled_video) > 0:
                print(f"SRT altyazılar başarıyla eklendi: {subtitled_video}")
                with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                    log_file.write("SRT altyazı ekleme başarılı!\n\n")
                return subtitled_video
            else:
                # SRT başarısız olduysa drawtext yöntemini dene
                with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                    log_file.write("SRT altyazı ekleme başarısız oldu, drawtext yöntemi deneniyor...\n\n")
                
                # drawtext yöntemi - altyazıları iki yarıya bölerek ekle
                filter_texts = []
                current_time = 0
                
                # Güvenli font yolu 
                if font_path and os.path.exists(font_path):
                    # Mutlak yol kullan ve tüm \ karakterlerini \\ yap
                    safe_font_path = font_path.replace('\\', '\\\\')
                    # Windows yollarında : karakteri var, bunları da kaçış karakteri ekleyelim
                    if ':' in safe_font_path:
                        safe_font_path = safe_font_path.replace(':', '\\:')
                    font_param = f"fontfile='{safe_font_path}':"
                else:
                    font_param = ""
                
                for i, sentence in enumerate(sentences):
                    # Zamanlamayı ses dosyalarına göre hesapla
                    if i < len(audio_durations):
                        total_duration = audio_durations[i]
                        first_half_start = current_time
                        first_half_end = current_time + (total_duration / 2)
                        second_half_start = first_half_end
                        second_half_end = current_time + total_duration
                        current_time = second_half_end + 0.1  # Küçük bir boşluk ekle
                    else:
                        total_duration = duration / max(1, len(sentences))
                        first_half_start = i * total_duration
                        first_half_end = first_half_start + (total_duration / 2)
                        second_half_start = first_half_end
                        second_half_end = (i + 1) * total_duration
                    
                    # Cümleyi daha anlamlı bir şekilde böl
                    sentence = sentence.strip()
                    
                    # Noktalama işaretlerini kontrol et (virgül, noktalı virgül, iki nokta)
                    punctuation_marks = [',', ';', ':']
                    best_split_point = -1
                    
                    # Cümlenin ortasına yakın bir noktalama işareti bul
                    sentence_length = len(sentence)
                    mid_point = sentence_length // 2
                    
                    # Ortaya en yakın noktalama işaretini bul
                    min_distance = sentence_length
                    for idx, char in enumerate(sentence):
                        if char in punctuation_marks:
                            distance = abs(idx - mid_point)
                            if distance < min_distance:
                                min_distance = distance
                                best_split_point = idx + 1  # Noktalama işaretinden sonra böl
                    
                    # Eğer uygun noktalama işareti bulunamazsa, en yakın boşluğu bul
                    if best_split_point == -1:
                        min_distance = sentence_length
                        for idx, char in enumerate(sentence):
                            if char == ' ':
                                distance = abs(idx - mid_point)
                                if distance < min_distance:
                                    min_distance = distance
                                    best_split_point = idx
                    
                    # Hala bölme noktası bulunamadıysa, ortadan böl
                    if best_split_point == -1:
                        best_split_point = mid_point
                    
                    first_half = sentence[:best_split_point].strip()
                    second_half = sentence[best_split_point:].strip()
                    
                    # Özel karakterleri temizle
                    first_half = first_half.replace("'", "").replace('"', "").replace(':', "").replace('\\', "")
                    second_half = second_half.replace("'", "").replace('"', "").replace(':', "").replace('\\', "")
                    
                    # İlk yarı için filtre ekle
                    filter_text = f"drawtext={font_param}fontsize=45:fontcolor=white:box=1:boxcolor=black@0.85:boxborderw=10:x=(w-text_w)/2:y=h*0.75:text='{first_half}':enable='between(t,{first_half_start},{first_half_end})'"
                    filter_texts.append(filter_text)
                    
                    # İkinci yarı için filtre ekle
                    filter_text = f"drawtext={font_param}fontsize=45:fontcolor=white:box=1:boxcolor=black@0.85:boxborderw=10:x=(w-text_w)/2:y=h*0.75:text='{second_half}':enable='between(t,{second_half_start},{second_half_end})'"
                    filter_texts.append(filter_text)
                
                # Tüm filtreleri birleştir
                all_filters = ",".join(filter_texts)
                
                # FFmpeg komutunu hazırla ve çalıştır
                subtitle_cmd = f'"{ffmpeg_path}" -i "{os.path.abspath(video_path)}" -vf "{all_filters}" -c:a copy "{os.path.abspath(subtitled_video)}"'
                
                with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                    log_file.write("--- Drawtext Altyazı Komutu ---\n")
                    log_file.write(f"{subtitle_cmd}\n\n")
                
                print("Drawtext altyazı komutu çalıştırılıyor...")
                
                try:
                    result = subprocess.run(subtitle_cmd, shell=True, capture_output=True, text=True)
                    with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                        log_file.write("Drawtext komut çıktısı:\n")
                        log_file.write(f"STDOUT: {result.stdout}\n")
                        log_file.write(f"STDERR: {result.stderr}\n\n")
                    
                    # Başarılı olup olmadığını kontrol et
                    if os.path.exists(subtitled_video) and os.path.getsize(subtitled_video) > 0:
                        print(f"Drawtext altyazılar başarıyla eklendi: {subtitled_video}")
                        with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                            log_file.write("Drawtext altyazı ekleme başarılı!\n\n")
                        return subtitled_video
                    else:
                        # Son çare: orijinal videoyu kopyala
                        print("Altyazı eklenemedi, orijinal video kopyalanıyor...")
                        shutil.copy2(video_path, subtitled_video)
                        return subtitled_video
                        
                except Exception as e:
                    print(f"Drawtext altyazı hatası: {str(e)}")
                    # Son çare: orijinal videoyu kopyala
                    shutil.copy2(video_path, subtitled_video)
                    return subtitled_video
                
        except Exception as e:
            print(f"SRT altyazı hatası: {str(e)}")
            # Orijinal videoyu kopyala
            shutil.copy2(video_path, subtitled_video)
            return subtitled_video
        
    except Exception as e:
        print(f"Altyazı ekleme genel hatası: {str(e)}")
        # Hata durumunda orijinal videoyu kopyala
        try:
            with open(subtitle_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"Genel hata: {str(e)}\n")
                log_file.write("=== Altyazı İşlemi Sonu (Hata) ===\n")
            
            shutil.copy2(video_path, os.path.join(project_folder, "subtitled_video.mp4"))
            return os.path.join(project_folder, "subtitled_video.mp4")
        except Exception as copy_error:
            print(f"Dosya kopyalama hatası: {str(copy_error)}")
            # Son çare
            with open(os.path.join(project_folder, "subtitled_video.mp4"), 'wb') as f:
                f.write(b'')
            return os.path.join(project_folder, "subtitled_video.mp4")

def format_srt_time(seconds):
    """
    Saniye cinsinden süreyi SRT formatında zaman damgasına dönüştürür
    
    Args:
        seconds (float): Saniye cinsinden süre
        
    Returns:
        str: SRT formatında zaman damgası (HH:MM:SS,MS)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

def format_ass_time(seconds: float) -> str:
    """
    Saniye cinsinden süreyi ASS formatında zaman damgasına dönüştürür
    
    Args:
        seconds (float): Saniye cinsinden süre
        
    Returns:
        str: ASS formatında zaman damgası (H:MM:SS.cs)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    centiseconds = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02d}:{int(seconds):02d}.{centiseconds:02d}"

def load_word_timings(project_folder: str) -> List[Dict[str, Any]]:
    """
    Whisper API ile oluşturulan kelime zamanlamalarını yükler
    
    Args:
        project_folder (str): Proje klasörünün yolu
    
    Returns:
        List[Dict[str, Any]]: Kelime zamanlamalarını içeren liste
    """
    tts_folder = os.path.join(project_folder, "tts_audio")
    timings = []
    
    if not os.path.exists(tts_folder):
        print(f"TTS klasörü bulunamadı: {tts_folder}")
        return timings
    
    # Önce birleştirilmiş ses dosyasının kelime zamanlamalarını kontrol et
    full_timing_path = os.path.join(tts_folder, "full_timing.json")
    if os.path.exists(full_timing_path):
        try:
            with open(full_timing_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Geçerli kelime zamanlamaları var mı kontrol et
                if isinstance(data, dict) and "words" in data and isinstance(data["words"], list):
                    # Kelime zamanlamaları var, doğru formatta
                    print(f"Birleştirilmiş ses dosyasının kelime zamanlamaları bulundu: {len(data['words'])} kelime")
                    return [data]  # Tek bir zamanlama verisi döndür
                elif isinstance(data, dict) and "segments" in data and isinstance(data["segments"], list):
                    # Whisper API'nin farklı bir formatı, segments'ten words'e dönüştür
                    words = []
                    for segment in data["segments"]:
                        if "words" in segment and isinstance(segment["words"], list):
                            words.extend(segment["words"])
                    
                    if words:
                        print(f"Birleştirilmiş ses dosyasının kelime zamanlamaları (segments formatında) bulundu: {len(words)} kelime")
                        return [{"text": data.get("text", ""), "words": words}]
                else:
                    print(f"Geçersiz zamanlama formatı: {full_timing_path}")
        except Exception as e:
            print(f"Birleştirilmiş zamanlama dosyası yükleme hatası: {str(e)}")
    
    # Birleştirilmiş zamanlama dosyası yoksa veya geçersizse, eski yöntemi kullan
    print("Birleştirilmiş zamanlama dosyası bulunamadı, ayrı zamanlama dosyalarını kontrol ediliyor...")
    
    # Zamanlama dosyalarını bul
    timing_files = []
    for file in os.listdir(tts_folder):
        if file.startswith("timing_") and file.endswith(".json"):
            timing_files.append(os.path.join(tts_folder, file))
    
    # Dosyaları sırala
    timing_files.sort()
    
    # Her dosyayı yükle
    for timing_file in timing_files:
        try:
            with open(timing_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Geçerli kelime zamanlamaları var mı kontrol et
                if isinstance(data, dict) and "words" in data and isinstance(data["words"], list):
                    # Kelime zamanlamaları var, doğru formatta
                    timings.append(data)
                elif isinstance(data, dict) and "segments" in data and isinstance(data["segments"], list):
                    # Whisper API'nin farklı bir formatı, segments'ten words'e dönüştür
                    words = []
                    for segment in data["segments"]:
                        if "words" in segment and isinstance(segment["words"], list):
                            words.extend(segment["words"])
                    
                    if words:
                        timings.append({"text": data.get("text", ""), "words": words})
                else:
                    print(f"Geçersiz zamanlama formatı: {timing_file}")
        except Exception as e:
            print(f"Zamanlama dosyası yükleme hatası: {str(e)}")
    
    return timings

def create_word_level_srt(sentences: List[str], timings: List[Dict[str, Any]], output_path: str) -> bool:
    """
    Kelime seviyesinde zamanlamalara sahip SRT dosyası oluşturur
    
    Args:
        sentences (List[str]): Altyazı cümleleri
        timings (List[Dict[str, Any]]): Kelime zamanlamaları
        output_path (str): Çıktı SRT dosyasının yolu
    
    Returns:
        bool: Başarılı ise True, değilse False
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            subtitle_index = 1
            cumulative_time = 0.0  # Kümülatif zaman
            last_subtitle_end = 0.0  # Son altyazının bitiş zamanı
            
            # Önce ses dosyalarının sürelerini hesapla
            audio_durations = []
            for timing_data in timings:
                if "words" not in timing_data or not timing_data["words"]:
                    audio_durations.append(0.0)
                    continue
                
                words = timing_data["words"]
                if not words:
                    audio_durations.append(0.0)
                    continue
                
                # Son kelimenin bitiş zamanını al
                last_word = words[-1]
                if "end" in last_word:
                    audio_durations.append(last_word["end"])
                else:
                    audio_durations.append(0.0)
            
            # Her ses dosyası için altyazıları oluştur
            for i, timing_data in enumerate(timings):
                if "words" not in timing_data or not timing_data["words"]:
                    cumulative_time += audio_durations[i] + 0.2  # Ses dosyası arasında boşluk bırak (0.2 saniye)
                    continue
                
                words = timing_data["words"]
                if not words:
                    cumulative_time += audio_durations[i] + 0.2
                    continue
                
                # Cümle başlangıç ve bitiş zamanlarını belirle
                sentence_start = words[0]["start"] + cumulative_time if "start" in words[0] else cumulative_time
                sentence_end = words[-1]["end"] + cumulative_time if "end" in words[-1] else cumulative_time + audio_durations[i]
                
                # Kelimeleri daha akıllı bir şekilde grupla
                word_groups = []
                current_group = []
                current_group_word_count = 0
                max_words_per_group = 7  # Bir grupta maksimum kelime sayısı
                
                # Noktalama işaretleri ve bağlaçlar
                end_punctuation = ['.', '!', '?']  # Cümle sonu noktalama işaretleri
                mid_punctuation = [',', ';', ':']  # Cümle içi noktalama işaretleri
                conjunctions = ["ve", "veya", "ile", "ya", "ama", "fakat", "ancak", "çünkü", "bu", "şu", "o"]  # Bağlaçlar
                
                for j, word_info in enumerate(words):
                    if "word" not in word_info or "start" not in word_info or "end" not in word_info:
                        continue
                    
                    # Kelime bilgisini kopyala ve kümülatif zamanı ekle
                    adjusted_word_info = word_info.copy()
                    adjusted_word_info["start"] = word_info["start"] + cumulative_time
                    adjusted_word_info["end"] = word_info["end"] + cumulative_time
                    
                    # Kelimeyi gruba ekle
                    current_group.append(adjusted_word_info)
                    current_group_word_count += 1
                    
                    # Grup sonlandırma koşulları
                    word = word_info["word"].strip()
                    is_last_word = j == len(words) - 1
                    
                    # Cümle sonu noktalama işaretlerinde her zaman grup sonlandır
                    if any(word.endswith(p) for p in end_punctuation) or is_last_word:
                        word_groups.append(current_group)
                        current_group = []
                        current_group_word_count = 0
                    # Cümle içi noktalama işaretlerinde, grup yeterince uzunsa sonlandır
                    elif any(word.endswith(p) for p in mid_punctuation) and current_group_word_count >= 3:
                        word_groups.append(current_group)
                        current_group = []
                        current_group_word_count = 0
                    # Maksimum kelime sayısına ulaşıldıysa ve sonraki kelime bağlaç değilse grup sonlandır
                    elif current_group_word_count >= max_words_per_group:
                        # Sonraki kelimeye bak
                        if j + 1 < len(words) and words[j + 1]["word"].strip().lower() not in conjunctions:
                            word_groups.append(current_group)
                            current_group = []
                            current_group_word_count = 0
                
                # Son grubu ekle
                if current_group:
                    word_groups.append(current_group)
                
                # Her grup için altyazı oluştur
                for group in word_groups:
                    if not group:
                        continue
                    
                    start_time = group[0]["start"]
                    end_time = group[-1]["end"]
                    
                    # Çakışan zamanları önle - önceki altyazının bitiş zamanından sonra başlat
                    if start_time < last_subtitle_end + 0.2:  # 0.2 saniyelik güvenlik boşluğu
                        start_time = last_subtitle_end + 0.2
                    
                    # Kelime sayısına göre minimum süre hesapla
                    word_count = len(group)
                    min_duration = max(1.0, word_count * 0.3)  # En az 1 saniye veya kelime başına 0.3 saniye
                    
                    # Minimum süre kontrolü
                    if end_time - start_time < min_duration:
                        end_time = start_time + min_duration
                    
                    # Grup metnini oluştur
                    text = " ".join([w["word"] for w in group])
                    
                    # SRT girişi ekle
                    f.write(f"{subtitle_index}\n")
                    f.write(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}\n")
                    f.write(f"{text}\n\n")
                    
                    # Son altyazının bitiş zamanını güncelle
                    last_subtitle_end = end_time
                    subtitle_index += 1
                
                # Bir sonraki ses dosyası için kümülatif zamanı güncelle
                # Ses dosyası arasında daha büyük bir boşluk bırak (0.2 saniye)
                cumulative_time += audio_durations[i] + 0.2
            
        return True
    except Exception as e:
        print(f"Kelime seviyesinde SRT oluşturma hatası: {str(e)}")
        return False
