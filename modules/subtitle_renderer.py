#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import json
import shutil
from typing import List, Dict, Any
from datetime import datetime
import logging

def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    milliseconds = int((secs - int(secs)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{milliseconds:03d}"

def format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    centiseconds = int((secs - int(secs)) * 100)
    return f"{hours}:{minutes:02d}:{int(secs):02d}.{centiseconds:02d}"

def load_word_timings(project_folder: str) -> List[Dict[str, Any]]:
    """Load word timings from Whisper API output"""
    tts_folder = os.path.join(project_folder, "tts_audio")
    timings = []
    log_path = os.path.join(project_folder, "subtitle_log.txt")
    
    if not os.path.exists(tts_folder):
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"TTS folder not found: {tts_folder}\n")
        return timings
    
    full_timing_path = os.path.join(tts_folder, "full_timing.json")
    if os.path.exists(full_timing_path):
        try:
            with open(full_timing_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"Loaded timing data keys: {list(data.keys())}\n")
        except Exception as e:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Error loading timing data: {str(e)}\n")
            return timings
            
            words = []
            
            # Farklı veri formatlarını kontrol et
            # 1. Düz words dizisi formatı
            if "words" in data and isinstance(data["words"], list):
                words = [w for w in data["words"] if "word" in w and "start" in w and "end" in w]
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"Found {len(words)} words in direct words field\n")
                    if words:
                        log.write(f"Sample word: {words[0]}\n")
            
            # 2. Segments formatı
            elif "segments" in data and isinstance(data["segments"], list):
                for segment in data["segments"]:
                    if "words" in segment:
                        segment_words = [w for w in segment["words"] 
                                         if "word" in w and "start" in w and "end" in w]
                        words.extend(segment_words)
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"Found {len(words)} words in segments\n")
            
            # 3. API v1+ için alternatif formatlar
            elif "result" in data:
                result = data["result"]
                if "words" in result:
                    words = [w for w in result["words"] if "word" in w and "start" in w and "end" in w]
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"Found {len(words)} words in result.words\n")
            
            # 4. Chunks formatı
            elif "chunks" in data:
                for chunk in data["chunks"]:
                    if "words" in chunk:
                        chunk_words = [w for w in chunk["words"] 
                                      if "word" in w and "start" in w and "end" in w]
                        words.extend(chunk_words)
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"Found {len(words)} words in chunks\n")
            
            # 5. Whisper OpenAI'nin yeni API yanıt formatı
            elif "text" in data and "duration" in data:
                if "words" in data:
                    # Bazı Whisper yanıtları farklı formatta "words" içerebilir
                    try:
                        with open(log_path, "a", encoding="utf-8") as log:
                            log.write(f"Checking special words format: {type(data['words'])}\n")
                            if isinstance(data['words'], list) and len(data['words']) > 0:
                                sample = data['words'][0]
                                log.write(f"Sample entry: {sample}\n")
                                if isinstance(sample, dict):
                                    log.write(f"Sample keys: {list(sample.keys())}\n")
                    except Exception as e:
                        with open(log_path, "a", encoding="utf-8") as log:
                            log.write(f"Error examining words: {str(e)}\n")
                            
                # Kelimeler bulunamadıysa, metni manuel bölümleme dene
                if not words and "text" in data:
                    text = data["text"]
                    # Metni boşluklarla ayır ve her kelimeye eşit zaman ata
                    duration = float(data.get("duration", 30))
                    manual_words = text.split()
                    word_duration = duration / len(manual_words) if manual_words else 0
                    
                    start_time = 0.0
                    for word in manual_words:
                        word_len = len(word) / 4  # Uzunluğa göre yaklaşık süre (4 harf = 1 saniye)
                        word_time = max(0.3, min(2.0, word_len))  # Min 0.3, maks 2 saniye
                        words.append({
                            "word": word,
                            "start": start_time,
                            "end": start_time + word_time
                        })
                        start_time += word_time
                    
                    with open(log_path, "a", encoding="utf-8") as log:
                        log.write(f"Created {len(words)} manual word timings from text\n")
            
            if words:
                # Geçerli kelime zamanlamaları bulundu
                return [{"text": data.get("text", ""), "words": words}]
            else:
                # Zamanlamalar bulunamadı, hata ayıklama bilgisi ekle
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write("No valid word timing data found in structure\n")
                    log.write(f"Keys in data: {list(data.keys())}\n")
                    
                    # Mevcut ise, segment yapısından örnek yazdır
                    if "segments" in data and data["segments"]:
                        first_segment = data["segments"][0]
                        log.write(f"First segment keys: {list(first_segment.keys())}\n")
                        if "words" in first_segment and first_segment["words"]:
                            log.write(f"First word in segment: {first_segment['words'][0]}\n")
                    
                    # Kelime zamanlamaları oluşturulamadığı için son çare olarak yalnızca cümleleri kullan
                    text = data.get("text", "")
                    if text:
                        sentences = [s.strip() for s in text.split('.') if s.strip()]
                        log.write(f"Falling back to {len(sentences)} sentences without word timings\n")
                        
                        # Her cümle için manuel zamanlama yap
                        manual_timings = []
                        duration = float(data.get("duration", 30))
                        sentence_time = duration / len(sentences) if sentences else 0
                        
                        start_time = 0.0
                        for sentence in sentences:
                            words = sentence.split()
                            if not words:
                                continue
                                
                            word_time = sentence_time / len(words)
                            sentence_words = []
                            
                            for word in words:
                                sentence_words.append({
                                    "word": word,
                                    "start": start_time,
                                    "end": start_time + word_time
                                })
                                start_time += word_time
                            
                            manual_timings.append({"text": sentence, "words": sentence_words})
                        
                        return manual_timings
                
        except Exception as e:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Error parsing timing JSON: {str(e)}\n")
                
    else:
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"Timing file not found: {full_timing_path}\n")
    
    return timings

def create_subtitle_files(timings: List[Dict[str, Any]], project_folder: str, video_path: str = None) -> Dict[str, str]:
    """Create word-based SRT and ASS subtitle files"""
    srt_path = os.path.join(project_folder, "subtitles.srt")
    ass_path = os.path.join(project_folder, "subtitles.ass")
    log_path = os.path.join(project_folder, "subtitle_log.txt")
    
    all_words = []
    cumulative_time = 0.0
    
    for timing_data in timings:
        if "words" in timing_data:
            audio_duration = timing_data["words"][-1]["end"] if timing_data["words"] else 0
            for word in timing_data["words"]:
                all_words.append({
                    "word": word["word"].strip(),
                    "start": word["start"] + cumulative_time,
                    "end": word["end"] + cumulative_time
                })
            cumulative_time += audio_duration + 0.1
    
    # Write SRT file
    with open(srt_path, "w", encoding="utf-8") as srt_file, open(log_path, "a", encoding="utf-8") as log:
        log.write(f"Creating SRT: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # SRT için daha iyi stiller
        for i, word in enumerate(all_words, 1):
            start = word["start"]
            end = min(word["end"] + 0.05, 
                     all_words[i]["start"] - 0.01 if i < len(all_words) else word["end"] + 0.05)
            if end - start < 0.15:
                end = start + 0.15
                
            # Kelime uzunluğuna göre font boyutu - daha görünür olması için her kelime büyük boyutta
            font_size = "18" if len(word["word"]) <= 6 else "15" if len(word["word"]) <= 10 else "12"
            
            # SRT dosyasına yaz - gelişmiş stil etiketi
            srt_file.write(f"{i}\n")
            srt_file.write(f"{format_srt_time(start)} --> {format_srt_time(end)}\n")
            
            # Daha iyi görünürlük için stil ekle - merkeze hizalı ve arka plan renkli
            srt_file.write(f'<font size="{font_size}" color="white"><b>{word["word"]}</b></font>\n\n')
    
    # Write ASS file (FFmpeg'in subtitles filtresi SRT'yi doğru işleyemediğinde ASS kullanılabilir)
    ass_header = """[Script Info]
Title: Word-based Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,10,10,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    with open(ass_path, "w", encoding="utf-8") as ass_file, open(log_path, "a", encoding="utf-8") as log:
        log.write(f"Creating ASS: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        ass_file.write(ass_header)
        
        # ASS dosyasına kelimeleri tek tek ekle - daha iyi görünüm için stil iyileştirmeleri
        for i, word in enumerate(all_words):
            start = format_ass_time(word["start"])
            end = format_ass_time(min(word["end"] + 0.05, 
                                    all_words[i+1]["start"] - 0.01 if i + 1 < len(all_words) else word["end"] + 0.1))
            if format_ass_time(word["end"]) == start:
                end = format_ass_time(word["start"] + 0.15)
                
            # Özel karakterleri escape et
            text = word["word"].replace("{", "\\{").replace("}", "\\}")
            
            # Arka plan rengi ve kalın yazı tipi ile daha iyi görünürlük
            styled_text = f"{{\\b1\\fs24\\c&HFFFFFF&\\3c&H000000&\\4c&H000000&}}{text}{{\\b0}}"
            ass_file.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{styled_text}\n")
    
    # Harici altyazı dosyaları oluşturma - video_path varsa
    if video_path:
        try:
            video_dir = os.path.dirname(video_path)
            ext_srt_path = os.path.join(video_dir, "subtitles.srt")
            ext_ass_path = os.path.join(video_dir, "subtitles.ass")
            shutil.copy2(srt_path, ext_srt_path)
            shutil.copy2(ass_path, ext_ass_path)
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"External subtitle files created in {video_dir}\n")
        except Exception as e:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Error creating external subtitle files: {str(e)}\n")
    
    return {"srt": srt_path, "ass": ass_path}

def render_subtitles(video_path: str, lines: List[str], timings: List[Dict[str, Any]], project_folder: str, 
                   subtitle_language: str = "tr", content_language: str = "tr", openai_api_key: str = None, 
                   font_path: str = None) -> str:
    """
    Renders subtitles onto a video
    Args:
        video_path (str): path to the video file
        lines (List[str]): list of lines to render
        timings (List[Dict[str, Any]]): list of word timings from whisper API
        project_folder (str): path to the project folder
        subtitle_language (str, optional): language code for subtitles. Defaults to "tr".
        content_language (str, optional): language code for content. Defaults to "tr".
        openai_api_key (str, optional): OpenAI API key for potential translation. Defaults to None.
        font_path (str, optional): Path to font file. Defaults to None.

    Returns:
        str: path to the output video file
    """
    # Giriş parametrelerini kontrol et - eğer timings None ise boş liste yap
    if timings is None:
        timings = []
    
    # Altyazı dili değişkenini global olarak tanımla (diğer fonksiyonlar için)
    globals()['subtitle_language'] = subtitle_language
    
    # FFmpeg yolunu ayarla - önce config.json'dan almayı dene
    ffmpeg_path = r"C:\Users\pc\Desktop\MMoto\bin\bin\ffmpeg.exe"  # Varsayılan değer
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if "ffmpeg_path" in config:
                    ffmpeg_path = config.get("ffmpeg_path")
                    if not os.path.isabs(ffmpeg_path):
                        # Göreceli yolu mutlak yola çevir
                        ffmpeg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ffmpeg_path)
    except Exception as e:
        pass  # Varsayılan değeri kullan
    
    # Log dosyası
    log_path = os.path.join(project_folder, "subtitle_log.txt")
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"Starting subtitle rendering with content_language={content_language}, subtitle_language={subtitle_language}\n")
        log.write(f"Video path: {video_path}, lines count: {len(lines)}, timings count: {len(timings)}\n")
    
    # Sonuç yolunu belirle
    output_video_path = os.path.join(project_folder, "video_with_subtitles.mp4")
    timings_json_path = os.path.join(project_folder, "word_timings.json")
    
    # Önce full_timing.json'ı word_timings.json'a kopyalayalım
    # Çünkü her durumda bu TTS tarafından oluşturulan dosyayı kullanacağız
    tts_folder = os.path.join(project_folder, "tts_audio")
    full_timing_path = os.path.join(tts_folder, "full_timing.json")
    
    if os.path.exists(full_timing_path) and not os.path.exists(timings_json_path):
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"Copying {full_timing_path} to {timings_json_path}\n")
        try:
            shutil.copy2(full_timing_path, timings_json_path)
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Successfully copied timing file\n")
        except Exception as e:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Error copying timing file: {str(e)}\n")
    
    # İçerik dili ve altyazı dili farklıysa çeviri yap
    if subtitle_language != content_language and openai_api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_api_key)
            
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Translating from {content_language} to {subtitle_language}...\n")
            
            # word_timings.json dosyasını yükle ve içindeki metni çevir
            if os.path.exists(timings_json_path):
                try:
                    with open(timings_json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Ana metni çıkar
                    source_text = data.get("text", "")
                    if not source_text and isinstance(lines, list) and lines:
                        source_text = " ".join([str(line) for line in lines])
                        
                    if source_text:
                        translated_text = None  # Başlangıç değeri olarak None ata
                        
                        # OpenAI API ile çeviri yap
                        try:
                            # Önce gpt-4o ile dene
                            response = client.chat.completions.create(
                                model="gpt-4o",  # Önce gpt-4o dene
                                messages=[
                                    {"role": "system", "content": f"You are a professional translator. Translate the following text from {content_language} to {subtitle_language}. Keep the translation natural and maintain the same tone. Only return the translated text without any explanations."},
                                    {"role": "user", "content": source_text}
                                ]
                            )
                            translated_text = response.choices[0].message.content
                        except Exception as e:
                            with open(log_path, "a", encoding="utf-8") as log:
                                log.write(f"First model attempt failed: {str(e)}, trying alternative model\n")
                            # Alternatif olarak gpt-4 dene
                            try:
                                response = client.chat.completions.create(
                                    model="gpt-4",  # Alternatif model
                                    messages=[
                                        {"role": "system", "content": f"You are a professional translator. Translate the following text from {content_language} to {subtitle_language}. Keep the translation natural and maintain the same tone. Only return the translated text without any explanations."},
                                        {"role": "user", "content": source_text}
                                    ]
                                )
                                translated_text = response.choices[0].message.content
                            except Exception as e2:
                                with open(log_path, "a", encoding="utf-8") as log:
                                    log.write(f"Second model attempt also failed: {str(e2)}, falling back to text-davinci-003\n")
                                # Son çare olarak text-davinci-003 dene (yaygın model)
                                try:
                                    response = client.completions.create(
                                        model="text-davinci-003",
                                        prompt=f"Translate the following text from {content_language} to {subtitle_language}. Keep the translation natural:\n\n{source_text}",
                                        max_tokens=1024,
                                        temperature=0.3
                                    )
                                    # Eski model formatına uyum için response yapısını ayarla
                                    translated_text = response.choices[0].text.strip()
                                    with open(log_path, "a", encoding="utf-8") as log:
                                        log.write(f"Used text-davinci-003 for translation\n")
                                except Exception as e3:
                                    with open(log_path, "a", encoding="utf-8") as log:
                                        log.write(f"All API translation attempts failed: {str(e3)}\n")
                                    translated_text = None
                        
                        # Çevirinin başarılı olup olmadığını kontrol et
                        if translated_text:
                            with open(log_path, "a", encoding="utf-8") as log:
                                log.write(f"Original text: {source_text[:50]}...\n")
                                log.write(f"Translated text: {translated_text[:50]}...\n")
                            
                            # Çevrilmiş metni JSON dosyasına da kaydet (gerekirse)
                            try:
                                # Mevcut JSON'a çevrilmiş metni ekle
                                data["translated_text"] = translated_text
                                data["subtitle_language"] = subtitle_language
                                
                                # JSON'ı güncelle
                                with open(timings_json_path, "w", encoding="utf-8") as f:
                                    json.dump(data, f, indent=2)
                                with open(log_path, "a", encoding="utf-8") as log:
                                    log.write(f"Updated JSON with translated text\n")
                            except Exception as e:
                                with open(log_path, "a", encoding="utf-8") as log:
                                    log.write(f"Error updating JSON with translation: {str(e)}\n")
                        else:
                            # API çeviri başarısız olduğunda basit bir çeviri yapma (dillere göre kelime değişimi)
                            with open(log_path, "a", encoding="utf-8") as log:
                                log.write("Translation API failed completely, using basic word substitution\n")
                            
                            # Burada temel dil çiftleri için basit bir çeviri ekleyebiliriz
                            # Örnek: Türkçe -> İngilizce'ye basit kelime değişimi
                            if content_language == "tr" and subtitle_language == "en":
                                # Basit kelime değişimi sözlüğü (yaygın Türkçe kelimelerin İngilizce karşılıkları)
                                tr_to_en = {
                                    # Temel bağlaçlar ve edatlar
                                    "ve": "and", "bir": "a", "bu": "this", "için": "for", "ile": "with",
                                    "olarak": "as", "var": "there is", "çok": "very", "daha": "more",
                                    "gibi": "like", "kadar": "until", "sonra": "after", "önce": "before",
                                    "şey": "thing", "zaman": "time", "gün": "day", "yıl": "year",
                                    "kişi": "person", "insan": "human", "nasıl": "how", "ne": "what",
                                    "neden": "why", "kim": "who", "nerede": "where", "ne zaman": "when",
                                    "ama": "but", "fakat": "however", "veya": "or", "ya da": "or",
                                    "şimdi": "now", "hemen": "immediately", "belki": "maybe", "kesinlikle": "definitely",
                                    
                                    # Yaygın fiiller
                                    "olmak": "to be", "yapmak": "to do", "gitmek": "to go", "gelmek": "to come",
                                    "görmek": "to see", "bilmek": "to know", "istemek": "to want", "almak": "to take",
                                    "vermek": "to give", "bulmak": "to find", "duymak": "to hear", "söylemek": "to say",
                                    "düşünmek": "to think", "konuşmak": "to speak", "anlamak": "to understand",
                                    
                                    # Yaygın sıfatlar
                                    "büyük": "big", "küçük": "small", "iyi": "good", "kötü": "bad",
                                    "güzel": "beautiful", "çirkin": "ugly", "hızlı": "fast", "yavaş": "slow",
                                    "eski": "old", "yeni": "new", "sıcak": "hot", "soğuk": "cold",
                                    "uzun": "long", "kısa": "short", "kolay": "easy", "zor": "difficult",
                                    
                                    # Bilimsel kelimeler
                                    "bilim": "science", "teknoloji": "technology", "keşif": "discovery",
                                    "araştırma": "research", "deney": "experiment", "teori": "theory",
                                    "geliştirmek": "to develop", "evren": "universe", "uzay": "space",
                                    "dünya": "world", "yaşam": "life", "canlı": "living",
                                    "mars": "mars", "gezegen": "planet", "yıldız": "star",
                                    "gizli": "secret", "hayat": "life", "belirtiler": "signs",
                                    "kanıt": "evidence", "mikroorganizma": "microorganism",
                                    "yüzey": "surface", "bulunmak": "to find", "açıklamak": "to explain",
                                    
                                    # Mars metni için özel kelimeler
                                    "şaşırtıcı": "surprising", "dikkat": "attention", "çekiyor": "draws",
                                    "inanılmaz": "incredible", "şoke": "shocked", "buluş": "finding",
                                    "benzerlik": "similarity", "gösteriyor": "shows", "dayanıklı": "resistant",
                                    "koşul": "condition", "aşırı": "extreme", "gerçek": "truth",
                                    "bilmediği": "unknown", "beklenmedik": "unexpected", "açıkladı": "announced",
                                    "somut": "concrete", "olabilir": "might be"
                                }
                                
                                # Metni kelimelere ayır
                                words = source_text.split()
                                # Basit kelime değişimi ile çeviri
                                translated_words = []
                                for word in words:
                                    lower_word = word.lower()
                                    # Kelime sözlükte varsa değiştir, yoksa aynı bırak
                                    if lower_word in tr_to_en:
                                        translated_words.append(tr_to_en[lower_word])
                                    else:
                                        translated_words.append(word)
                                
                                translated_text = " ".join(translated_words)
                                with open(log_path, "a", encoding="utf-8") as log:
                                    log.write(f"Basic substitution result: {translated_text[:50]}...\n")
                            else:
                                # Diğer dil çiftleri için orijinal metni kullan
                                translated_text = source_text
                                with open(log_path, "a", encoding="utf-8") as log:
                                    log.write("No translation method available, using original text\n")
                        
                        # Çevrilmiş metni word_by_word.srt dosyasına dönüştür
                        srt_path = os.path.join(project_folder, "word_by_word.srt")
                        words = []
                        
                        # Kelime zamanlamalarını al
                        if "words" in data and isinstance(data["words"], list):
                            words = [w for w in data["words"] if "word" in w and "start" in w and "end" in w]
                        
                        if words:
                            # Çevrilmiş metni kelimelere böl
                            translated_words = translated_text.split()
                            
                            # SRT dosyasını oluştur
                            with open(srt_path, "w", encoding="utf-8") as srt_file:
                                word_count = min(len(words), len(translated_words))
                                for i in range(word_count):
                                    # Orijinal kelime zamanlamalarını kullan ama çevrilmiş kelimeleri yaz
                                    start = format_srt_time(words[i]["start"])
                                    end = format_srt_time(words[i]["end"])
                                    text = translated_words[i]
                                    
                                    # Büyük fontlu, beyaz yazı, siyah arka plan
                                    styled_text = f'<font size="18" color="white"><b>{text}</b></font>'
                                    
                                    # SRT girişini yaz
                                    srt_file.write(f"{i+1}\n")
                                    srt_file.write(f"{start} --> {end}\n")
                                    srt_file.write(f"{styled_text}\n\n")
                            
                            with open(log_path, "a", encoding="utf-8") as log:
                                log.write(f"Created translated SRT with {word_count} words\n")
                            
                            # Çevrilmiş SRT ile video oluştur
                            cmd = f'"{ffmpeg_path}" -y -i "{video_path}" -vf "subtitles={srt_path}:force_style=\'Fontsize=18,Alignment=2,MarginV=60\'" -c:v libx264 -c:a copy "{output_video_path}"'
                            
                            with open(log_path, "a", encoding="utf-8") as log:
                                log.write(f"Running FFmpeg command: {cmd}\n")
                            
                            # Çalışma dizini değiştirerek çalıştır
                            process = subprocess.Popen(
                                cmd,
                                shell=True,
                                cwd=project_folder,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE
                            )
                            
                            stdout, stderr = process.communicate()
                            if process.returncode == 0 and os.path.exists(output_video_path):
                                with open(log_path, "a", encoding="utf-8") as log:
                                    log.write(f"Translated subtitles video created successfully\n")
                                return output_video_path
                except Exception as e:
                    with open(log_path, "a", encoding="utf-8") as log:
                        log.write(f"Error during translation process: {str(e)}\n")
        except Exception as e:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Translation failed: {str(e)}\n")
    
    # Kelime zamanlamaları JSON dosyasının varlığını kontrol et
    if os.path.exists(timings_json_path):
        # Doğrudan helper fonksiyonu kullan
        try:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Calling create_word_by_word_video with timing file: {timings_json_path}\n")
            
            success = create_word_by_word_video(
                video_path=video_path,
                timings_json_path=timings_json_path,
                output_path=output_video_path,
                ffmpeg_path=ffmpeg_path
            )
            
            # Başarılı ise direkt dön
            if success:
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"Successfully created subtitled video with create_word_by_word_video\n")
                return output_video_path
            else:
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"create_word_by_word_video returned false, trying alternative methods\n")
        except Exception as e:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Error in create_word_by_word_video: {str(e)}\n")
    
    # Önceki yöntemlerle devam et
    logging.info(f"Starting subtitle process for video: {video_path}")
    logging.info(f"Project folder: {project_folder}")
    
    if not timings:
        with open(os.path.join(project_folder, "subtitle_log.txt"), "a", encoding="utf-8") as log:
            log.write("No timings found, copying original video\n")
        shutil.copy2(video_path, output_video_path)
        return output_video_path
    
    # Eğer timings varsa ama JSON dosyası oluşturulmadıysa, JSON dosyasını oluştur
    if not os.path.exists(timings_json_path) and timings:
        with open(os.path.join(project_folder, "subtitle_log.txt"), "a", encoding="utf-8") as log:
            log.write("Creating word_timings.json from provided timings\n")
        try:
            with open(timings_json_path, "w", encoding="utf-8") as f:
                json_data = {"duration": 0, "language": subtitle_language, "words": []}
                
                # Eğer timings içinde words varsa
                all_words = []
                for timing_data in timings:
                    if "words" in timing_data:
                        all_words.extend(timing_data["words"])
                        if "text" in timing_data and not json_data.get("text"):
                            json_data["text"] = timing_data["text"]
                
                if all_words:
                    json_data["words"] = all_words
                    # En son kelimenin bitiş zamanını duration olarak kullan
                    if all_words[-1].get("end"):
                        json_data["duration"] = all_words[-1]["end"]
                else:
                    # Eğer kelimeler yoksa basit bir zamanlamalar dizisi oluştur
                    text = " ".join([line for line in lines if line and isinstance(line, str)])
                    json_data["text"] = text
                    word_list = text.split()
                    total_duration = 30.0  # varsayılan 30 saniye
                    word_time = total_duration / len(word_list) if word_list else 0.5
                    
                    start_time = 0.0
                    for word in word_list:
                        # Kelime uzunluğuna göre süre ayarla
                        word_len = len(word) / 4  # Uzunluğa göre yaklaşık süre (4 harf = 1 saniye)
                        word_duration = max(0.3, min(2.0, word_len))  # Min 0.3, maks 2 saniye
                        
                        json_data["words"].append({
                            "word": word,
                            "start": start_time,
                            "end": start_time + word_duration
                        })
                        start_time += word_duration
                    
                    json_data["duration"] = start_time
                
                json.dump(json_data, f, indent=2)
                
                # JSON dosyası oluşturulduktan sonra tekrar word-by-word video fonksiyonunu çağır
                success = create_word_by_word_video(
                    video_path=video_path,
                    timings_json_path=timings_json_path,
                    output_path=output_video_path,
                    ffmpeg_path=ffmpeg_path
                )
                
                if success:
                    return output_video_path
                        
        except Exception as e:
            with open(os.path.join(project_folder, "subtitle_log.txt"), "a", encoding="utf-8") as log:
                log.write(f"Error creating word_timings.json: {str(e)}\n")
    
    # video_path parametresini ileterek subtitle_files oluştur
    subtitle_files = create_subtitle_files(timings, project_folder, video_path)
    
    # Altyazıları yerleştirmek için çeşitli yöntemler deneyelim
    with open(os.path.join(project_folder, "subtitle_log.txt"), "a", encoding="utf-8") as log:
        # Windows yollarını FFmpeg için güvenli hale getir
        video_dir = os.path.dirname(video_path)
        ext_srt_path = os.path.join(video_dir, "subtitles.srt")
        ext_ass_path = os.path.join(video_dir, "subtitles.ass")
        
        # FFmpeg için yolları güvenli hale getir (Windows'ta çift ters slash gerekiyor)
        safe_video_path = video_path.replace("\\", "\\\\").replace(":", "\\:")
        safe_srt_path = ext_srt_path.replace("\\", "\\\\").replace(":", "\\:")
        
        log.write(f"Using safe paths for FFmpeg:\n")
        log.write(f"Video: {safe_video_path}\n")
        log.write(f"SRT: {safe_srt_path}\n")
        
        # 0. Yeni deneme: mp4box ile altyazı ekleme (daha yüksek uyumluluk)
        try:
            mp4box_path = os.path.join(os.path.dirname(ffmpeg_path), "mp4box.exe")
            if os.path.exists(mp4box_path):
                # Önce videoyu kopyala
                shutil.copy2(video_path, output_video_path)
                
                # MP4Box komutu oluştur
                mp4box_cmd = f'"{mp4box_path}" -add "{ext_srt_path}":lang={subtitle_language}:name="Subtitles" "{output_video_path}"'
                log.write(f"MP4Box command: {mp4box_cmd}\n")
                
                # Komutu çalıştır
                result = subprocess.run(mp4box_cmd, shell=True, capture_output=True, text=True)
                log.write(f"MP4Box stderr: {result.stderr}\n")
                
                if result.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
                    log.write("Subtitles added successfully with MP4Box\n")
                    return output_video_path
            else:
                log.write(f"MP4Box not found at {mp4box_path}\n")
        except Exception as e:
            log.write(f"MP4Box error: {str(e)}\n")
                
        # 1. Deneme: Muxing - altyazıyı video konteynerine ekle
        mux_cmd = [
            ffmpeg_path, "-y", "-i", video_path, "-i", ext_srt_path,
            "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
            "-metadata:s:s:0", f"language={subtitle_language}",
            output_video_path
        ]
        log.write(f"Running FFmpeg muxing command: {' '.join(mux_cmd)}\n")
        result = subprocess.run(mux_cmd, capture_output=True, text=True)
        log.write(f"Muxing stderr: {result.stderr}\n")
        
        if result.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
            log.write("Subtitles added successfully as external track\n")
            return output_video_path

        # 2. Deneme: Subtitles filtresi ile shell komut kullanarak (manuel saf shell komutu)
        try:
            # Basit shell komutu, subtitles filtresini her türlü encoding probleminden uzak tutar
            shell_cmd = f'"{ffmpeg_path}" -y -i "{video_path}" -vf subtitles=subtitles.srt:force_style="FontSize=18,Alignment=2,BorderStyle=4,Outline=2,Shadow=1,MarginV=60" -c:v libx264 -c:a copy "{output_video_path}"'
            
            log.write(f"Running direct shell command with relative path: {shell_cmd}\n")
            
            # İşlemi başlat - çalışma dizinini altyazı dosyasıyla aynı yap
            process = subprocess.Popen(
                shell_cmd, 
                shell=True,
                cwd=video_dir,  # Çalışma dizinini değiştir - subtitles.srt buradadır
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # İşlemi bekle ve çıktıları al
            stdout, stderr = process.communicate()
            log.write(f"Shell stderr: {stderr.decode('utf-8', errors='ignore')}\n")
            
            if process.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
                log.write("Subtitles added successfully with shell command and relative path\n")
                return output_video_path
                
        except Exception as e:
            log.write(f"Shell command error: {str(e)}\n")
        
        # 3. Basit SRT yöntemi - minimum FFmpeg filtresi kullanarak
        try:
            # Önce, çalışma dizininde basitleştirilmiş bir SRT dosyası oluştur
            simple_srt_path = os.path.join(video_dir, "simple.srt")
            with open(simple_srt_path, "w", encoding="utf-8") as simple_srt:
                # Basit bir SRT dosyası oluştur - tüm içerik tek bir altyazı olarak
                if timings and "text" in timings[0]:
                    text = timings[0]["text"]
                    simple_srt.write("1\n")
                    simple_srt.write("00:00:01,000 --> 00:00:30,000\n")
                    simple_srt.write(f"{text}\n\n")
                    log.write(f"Created simple SRT with single subtitle\n")
            
            # FFmpeg komutu oluştur - çok basit sadece bir filtreyle
            simple_cmd = f'"{ffmpeg_path}" -y -i "{video_path}" -vf subtitles=simple.srt -c:v libx264 -c:a copy "{output_video_path}"'
            log.write(f"Running simple SRT command: {simple_cmd}\n")
            
            # Komutu çalıştır
            process = subprocess.Popen(
                simple_cmd, 
                shell=True,
                cwd=video_dir,  # Çalışma dizinini değiştir
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # İşlemi bekle ve çıktıları al
            stdout, stderr = process.communicate()
            log.write(f"Simple SRT stderr: {stderr.decode('utf-8', errors='ignore')}\n")
            
            if process.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
                log.write("Subtitles added successfully with simple SRT\n")
                return output_video_path
                
        except Exception as e:
            log.write(f"Simple SRT error: {str(e)}\n")
            
        # 4. Deneme: TEXT dosyası yöntemi - FFmpeg metin filtresi kullanarak
        try:
            # Önce, çalışma dizininde bir TEXT dosyası oluştur
            text_file_path = os.path.join(video_dir, "subtitles.txt")
            with open(text_file_path, "w", encoding="utf-8") as text_file:
                # TEXT dosyasına metni yaz
                if timings and "text" in timings[0]:
                    text_file.write(timings[0]["text"])
                    log.write(f"Created TEXT file with content\n")
            
            # FFmpeg komutu oluştur - drawtext filtresiyle
            text_cmd = f'"{ffmpeg_path}" -y -i "{video_path}" -vf "drawtext=fontfile=/Windows/Fonts/Arial.ttf:textfile=subtitles.txt:reload=1:fontcolor=white:fontsize=12:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-text_w)/2:y=h-th-100" -c:v libx264 -c:a copy "{output_video_path}"'
            log.write(f"Running TEXT file command: {text_cmd}\n")
            
            # Komutu çalıştır
            process = subprocess.Popen(
                text_cmd, 
                shell=True,
                cwd=video_dir,  # Çalışma dizinini değiştir
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # İşlemi bekle ve çıktıları al
            stdout, stderr = process.communicate()
            log.write(f"TEXT file stderr: {stderr.decode('utf-8', errors='ignore')}\n")
            
            if process.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
                log.write("Text overlay added successfully\n")
                return output_video_path
                
        except Exception as e:
            log.write(f"TEXT file error: {str(e)}\n")
            
        # 5. Deneme: Filter complex kullanarak dene ve force_style ekle
        filter_complex_cmd = [
            ffmpeg_path, "-y", "-i", video_path,
            "-filter_complex", f"[0:v]subtitles={ext_srt_path}:force_style='FontSize=8,Alignment=2,MarginV=100'[v]", "-map", "[v]", "-map", "0:a",
            "-c:v", "libx264", "-c:a", "copy", "-shortest",
            output_video_path
        ]
        log.write(f"Filter complex command: {' '.join(filter_complex_cmd)}\n")
        result = subprocess.run(filter_complex_cmd, capture_output=True, text=True)
        log.write(f"Filter complex stderr: {result.stderr}\n")
        
        if result.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
            log.write("SRT subtitles added successfully with filter complex\n")
            return output_video_path
        
        # 6. Alternatif: ASS formatını dene (bazı Windows sistemlerinde daha iyi çalışabilir)
        ass_path = subtitle_files["ass"].replace("\\", "/")
        ext_ass_path = os.path.join(os.path.dirname(video_path), "subtitles.ass")
        shutil.copy2(subtitle_files["ass"], ext_ass_path)
        
        ass_cmd = [
            ffmpeg_path, "-y", "-i", video_path,
            "-vf", f"ass={ext_ass_path}",
            "-c:v", "libx264", "-c:a", "copy", "-shortest",
            output_video_path
        ]
        log.write(f"ASS command: {' '.join(ass_cmd)}\n")
        result = subprocess.run(ass_cmd, capture_output=True, text=True)
        log.write(f"ASS stderr: {result.stderr}\n")
        
        if result.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
            log.write("ASS subtitles added successfully\n")
            return output_video_path
        
        # 7. Alternatif: ASS ile shell komutu
        ass_shell_cmd = f'"{ffmpeg_path}" -y -i "{video_path}" -vf "ass={ext_ass_path}" -c:v libx264 -c:a copy -shortest "{output_video_path}"'
        log.write(f"ASS shell command: {ass_shell_cmd}\n")
        result = subprocess.run(ass_shell_cmd, shell=True, capture_output=True, text=True)
        log.write(f"ASS shell stderr: {result.stderr}\n")
        
        if result.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
            log.write("ASS subtitles added successfully with shell command\n")
            return output_video_path
        
        # 8. Son çare: libass ile dene (genellikle daha iyi SRT desteği)
        try:
            log.write("Trying libass method\n")
            # local_srt_path = os.path.join(os.path.dirname(video_path), "subtitles.srt")
            # shutil.copy2(subtitle_files["srt"], local_srt_path)
            
            # Tam dosya adı olmadan, sadece dosya adını kullan - relative path
            srt_filename = os.path.basename(ext_srt_path)
            
            # libass ile shell komutunu çalıştır
            libass_cmd = f'"{ffmpeg_path}" -y -i "{video_path}" -vf "subtitles={srt_filename}" -c:v libx264 -c:a copy "{output_video_path}"'
            log.write(f"libass command: {libass_cmd}\n")
            
            # Komutu çalıştır
            process = subprocess.Popen(
                libass_cmd,
                shell=True, 
                cwd=os.path.dirname(video_path),  # Çalışma dizinini altyazı dosyasıyla aynı dizin yap
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            log.write(f"libass stderr: {stderr.decode('utf-8', errors='ignore')}\n")
            
            if process.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
                log.write("Subtitles added successfully with libass\n")
                return output_video_path
        except Exception as e:
            log.write(f"libass method failed: {str(e)}\n")
        
        # Tüm denemeler başarısız oldu, orijinal videoyu kopyala
        log.write("All subtitle attempts failed, copying original video\n")
        shutil.copy2(video_path, output_video_path)
    
    return output_video_path

if __name__ == "__main__":
    # Test usage
    project_folder = r"C:\Users\pc\Desktop\MMoto\output\video_2025-04-10_00-45-21"
    video_path = r"C:\Users\pc\Desktop\MMoto\output\video_2025-04-10_00-45-21\video_with_audio.mp4"
    render_subtitles(video_path, ["test"], None, project_folder)

# Ekstra: Altyazıları Word by Word eklemek için helper fonksiyon
def create_word_by_word_video(video_path: str, timings_json_path: str = None, output_path: str = None, ffmpeg_path: str = None):
    """
    Kelime kelime altyazı ekleyen özel fonksiyon.
    Bu fonksiyon, normal render_subtitles çalışmadığında doğrudan kullanılabilir.
    
    Args:
        video_path (str): Giriş video dosyası
        timings_json_path (str, optional): Kelime zamanlamalarını içeren JSON dosyası. None ise otomatik bulunur.
        output_path (str, optional): Çıkış video dosyası. None ise otomatik oluşturulur.
        ffmpeg_path (str, optional): FFmpeg yolu (None ise varsayılan kullanılır)
    """
    # FFmpeg yolunu ayarla
    if ffmpeg_path is None:
        # Varsayılan FFmpeg yolunu ayarla - önce config.json'dan almayı dene
        ffmpeg_path = r"C:\Users\pc\Desktop\MMoto\bin\bin\ffmpeg.exe"  # Varsayılan değer
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if "ffmpeg_path" in config:
                        ffmpeg_path = config.get("ffmpeg_path")
                        if not os.path.isabs(ffmpeg_path):
                            ffmpeg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ffmpeg_path)
        except Exception:
            pass  # Varsayılan değeri kullan
    
    # Proje klasörünü bul
    if video_path:
        project_folder = os.path.dirname(video_path)
    else:
        raise ValueError("Video path must be provided")
    
    # Çıkış yolunu ayarla
    if output_path is None:
        output_path = os.path.join(project_folder, "video_with_subtitles.mp4")
    
    # JSON yolunu ayarla
    if timings_json_path is None:
        # Olası JSON dosya yollarını kontrol et
        possible_paths = [
            os.path.join(project_folder, "word_timings.json"),
            os.path.join(project_folder, "tts_audio", "full_timing.json"),
            os.path.join(project_folder, "tts_audio", "timing.json"),
            os.path.join(project_folder, "timing.json")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                timings_json_path = path
                break
        
        if timings_json_path is None:
            print("JSON dosyası bulunamadı, fonksiyon işlemi iptal edildi")
            return False
    
    # Log dosyasını hazırla
    log_path = os.path.join(project_folder, "subtitle_log.txt")
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"Word by word subtitling started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Using timings file: {timings_json_path}\n")
    
    # Yapılandırma dosyasını yükle
    config = None
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
    except Exception as e:
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"Yapılandırma yükleme hatası: {str(e)}\n")
    
    # Altyazı ve içerik dillerini al
    content_language = "tr"  # varsayılan
    subtitle_language = "tr"  # varsayılan
    
    if config:
        content_language = config.get("content_language", "tr")
        subtitle_language = config.get("subtitle_language", "tr")
    
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"Content language: {content_language}, Subtitle language: {subtitle_language}\n")
    
    # JSON dosyasını yükle
    try:
        with open(timings_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Successfully loaded JSON data with keys: {list(data.keys())}\n")
    except Exception as e:
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"JSON yükleme hatası: {str(e)}\n")
        return False
    
    # Kelime zamanlamalarını çıkar
    words = []
    
    # 1. Düz 'words' dizisi formatını kontrol et
    if "words" in data and isinstance(data["words"], list):
        words = [w for w in data["words"] if "word" in w and "start" in w and "end" in w]
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"Found {len(words)} words in direct 'words' field\n")
    
    # 2. 'segments' formatını kontrol et
    elif "segments" in data and isinstance(data["segments"], list):
        for segment in data["segments"]:
            if "words" in segment:
                segment_words = [w for w in segment["words"] if "word" in w and "start" in w and "end" in w]
                words.extend(segment_words)
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"Found {len(words)} words in 'segments' field\n")
    
    # Kelimeler bulunamazsa çık
    if not words:
        with open(log_path, "a", encoding="utf-8") as log:
            log.write("JSON dosyasında kelime zamanlamaları bulunamadı\n")
        return False
    
    # Diğer dile çeviri ihtiyacı kontrolü ve çevrilmiş metni al
    translated_text = None
    
    # Önce JSON dosyasında translated_text alanını kontrol et
    if content_language != subtitle_language:
        try:
            if "translated_text" in data and data["translated_text"] and isinstance(data["translated_text"], str):
                translated_text = data["translated_text"]
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"Found translated text in JSON: {translated_text[:50]}...\n")
        except Exception as e:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Error checking translated_text in JSON: {str(e)}\n")
    
    # Eğer JSON'da çeviri yoksa önceden çevirdiğimiz SRT dosyasını kontrol et
    translated_srt_path = os.path.join(project_folder, "word_by_word.srt")
    if os.path.exists(translated_srt_path) and content_language != subtitle_language:
        # SRT'den çevirinin olup olmadığını kontrol et
        try:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Checking for existing translated SRT at {translated_srt_path}\n")
            
            with open(translated_srt_path, "r", encoding="utf-8") as srt_file:
                lines = srt_file.readlines()
                
                # SRT içeriğinden çevirilen metni çıkar
                translated_words = []
                for i in range(2, len(lines), 4):  # Her 4 satırda bir metin satırı var (1-index, timestamp, text, boş satır)
                    if i < len(lines):
                        # Metin satırındaki HTML etiketlerini temizle
                        line = lines[i].strip()
                        if "<font" in line and "</font>" in line:
                            # <font...><b>WORD</b></font> formatından WORD'ü çıkar
                            word = line.split("<b>")[1].split("</b>")[0] if "<b>" in line and "</b>" in line else ""
                            if word:
                                translated_words.append(word)
                
                if translated_words:
                    with open(log_path, "a", encoding="utf-8") as log:
                        log.write(f"Found {len(translated_words)} translated words in existing SRT\n")
                    
                    # Çevrilen kelimeleri kaydet
                    translated_text = " ".join(translated_words)
        except Exception as e:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Error extracting translations from SRT: {str(e)}\n")
    
    # Çevrilmiş SRT ve kelimeler var mı kontrol et
    if translated_text and content_language != subtitle_language:
        translated_words = translated_text.split()
        
        # Yeni SRT dosyası oluştur
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"Creating SRT with {len(translated_words)} translated words\n")
        
        # Yeniden SRT dosyası oluştur
        with open(translated_srt_path, "w", encoding="utf-8") as srt_file:
            # Minimum kelime sayısını belirle
            word_count = min(len(words), len(translated_words))
            for i in range(word_count):
                # Orijinal kelime zamanlamalarını kullan ama çevrilmiş kelimeleri yaz
                start = format_srt_time(words[i]["start"])
                end = format_srt_time(words[i]["end"])
                text = translated_words[i]
                
                # Büyük fontlu, beyaz yazı, siyah arka plan
                styled_text = f'<font size="18" color="white"><b>{text}</b></font>'
                
                # SRT girişini yaz
                srt_file.write(f"{i+1}\n")
                srt_file.write(f"{start} --> {end}\n")
                srt_file.write(f"{styled_text}\n\n")
            
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Created SRT with {word_count} translated words\n")
    else:
        # Çeviri yoksa normal SRT dosyası oluştur
        srt_path = os.path.join(project_folder, "word_by_word.srt")
        with open(srt_path, "w", encoding="utf-8") as srt_file, open(log_path, "a", encoding="utf-8") as log:
            log.write(f"Creating SRT file at {srt_path} with original words\n")
            for i, word in enumerate(words, 1):
                # SRT formatına dönüştür
                start = format_srt_time(word["start"])
                end = format_srt_time(word["end"])
                text = word["word"].strip()
                
                # Büyük fontlu, beyaz yazı, siyah arka plan
                styled_text = f'<font size="18" color="white"><b>{text}</b></font>'
                
                # SRT girişini yaz
                srt_file.write(f"{i}\n")
                srt_file.write(f"{start} --> {end}\n")
                srt_file.write(f"{styled_text}\n\n")
            
            log.write(f"Added {len(words)} words to SRT file\n")
    
    # Altyazılı videoyu oluştur - relative path kullanarak
    srt_file_name = os.path.basename(translated_srt_path)
    cmd = f'"{ffmpeg_path}" -y -i "{video_path}" -vf "subtitles={srt_file_name}:force_style=\'Fontsize=18,Alignment=2,MarginV=60\'" -c:v libx264 -c:a copy "{output_path}"'
    
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"Running FFmpeg command: {cmd}\n")
    
    # Çalışma dizini değiştirerek çalıştır
    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=project_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_path):
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"Kelime kelime altyazılı video başarıyla oluşturuldu: {output_path}\n")
            return True
        else:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write(f"FFmpeg hatası: {stderr.decode('utf-8', errors='ignore')}\n")
            return False
    except Exception as e:
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"İşlem hatası: {str(e)}\n")
        return False