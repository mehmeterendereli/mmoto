#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import tempfile
import shutil
import re
from typing import List, Dict, Any
from openai import OpenAI
import subprocess

def convert_numbers_to_text(text: str) -> str:
    """
    Metindeki sayıları yazıya çevirir (1881 -> bin sekiz yüz seksen bir)
    
    Args:
        text (str): Sayıları yazıya çevrilecek metin
    
    Returns:
        str: Sayıları yazıya çevrilmiş metin
    """
    # Regex ile sayıları bul
    def number_to_text(match):
        num = int(match.group(0))
        # Sayıyı yazıya çevir
        return convert_single_number_to_text(num)
    
    # Metindeki tüm sayıları yazıya çevir
    return re.sub(r'\b\d+\b', number_to_text, text)

def convert_single_number_to_text(num: int) -> str:
    """
    Tek bir sayıyı yazıya çevirir
    
    Args:
        num (int): Yazıya çevrilecek sayı
    
    Returns:
        str: Yazıya çevrilmiş sayı
    """
    birler = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
    onlar = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
    
    if num == 0:
        return "sıfır"
    
    if num < 0:
        return "eksi " + convert_single_number_to_text(-num)
    
    if num < 10:
        return birler[num]
    
    if num < 100:
        return onlar[num // 10] + (" " + birler[num % 10] if num % 10 != 0 else "")
    
    if num < 1000:
        yuzler = "yüz" if num // 100 == 1 else birler[num // 100] + " yüz"
        return yuzler + (" " + convert_single_number_to_text(num % 100) if num % 100 != 0 else "")
    
    if num < 1000000:
        binler = "bin" if num // 1000 == 1 else convert_single_number_to_text(num // 1000) + " bin"
        return binler + (" " + convert_single_number_to_text(num % 1000) if num % 1000 != 0 else "")
    
    if num < 1000000000:
        milyonlar = convert_single_number_to_text(num // 1000000) + " milyon"
        return milyonlar + (" " + convert_single_number_to_text(num % 1000000) if num % 1000000 != 0 else "")
    
    # Milyarlar
    milyarlar = convert_single_number_to_text(num // 1000000000) + " milyar"
    return milyarlar + (" " + convert_single_number_to_text(num % 1000000000) if num % 1000000000 != 0 else "")

def analyze_audio_with_whisper(audio_path: str, api_key: str) -> Dict[str, Any]:
    """
    Ses dosyasını Whisper API ile analiz ederek kelime seviyesinde zamanlama bilgisi çıkarır
    
    Args:
        audio_path (str): Analiz edilecek ses dosyasının yolu
        api_key (str): OpenAI API anahtarı
    
    Returns:
        Dict[str, Any]: Kelime zamanlamalarını içeren sözlük
    """
    try:
        client = OpenAI(api_key=api_key)
        
        with open(audio_path, "rb") as audio_file:
            # Güncellenmiş parametrelerle API çağrısı yap
            try:
                # Eski Whisper API (pre-v1) için deneme
                transcript = client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-1",
                    response_format="verbose_json",
                    timestamp_granularities=["word"]
                )
                
                # Bu noktaya gelinirse, çağrı başarılıydı
                print("Whisper API (new format) call successful")
                
                # TranscriptionVerbose nesnesini dict'e dönüştür
                if hasattr(transcript, "model_dump"):
                    # Pydantic v2 için
                    transcript_dict = transcript.model_dump()
                elif hasattr(transcript, "dict"):
                    # Pydantic v1 için
                    transcript_dict = transcript.dict()
                else:
                    # Nesne zaten dict ise
                    transcript_dict = dict(transcript)
                
                return transcript_dict
            except Exception as e:
                # Yeni format başarısız olursa, alternatif format dene
                print(f"New Whisper API format error: {str(e)}")
                print("Trying with alternative format...")
                
                # Dosyayı tekrar aç
                audio_file.seek(0)
                try:
                    # Farklı parametrelerle tekrar dene
                    transcript = client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-1",
                        response_format="verbose_json"  # timestamp_granularities olmadan dene
                    )
                    
                    # Bu formatta kelime zamanlamaları olmayabilir, manuel olarak oluşturulacak
                    print("Alternative Whisper API call successful (may not have word timings)")
                    
                    # TranscriptionVerbose nesnesini dict'e dönüştür
                    if hasattr(transcript, "model_dump"):
                        transcript_dict = transcript.model_dump()
                    elif hasattr(transcript, "dict"):
                        transcript_dict = transcript.dict()
                    else:
                        transcript_dict = dict(transcript)
                    
                    return transcript_dict
                except Exception as alt_error:
                    # İkinci deneme de başarısız olursa, elle özel format oluştur
                    print(f"Alternative Whisper API format error: {str(alt_error)}")
                    print("Creating manual transcript object...")
                    
                    # Dosyayı tekrar aç
                    audio_file.seek(0)
                    
                    # En basit formatta sesi metne çevir
                    basic_transcript = client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-1",
                        response_format="text"
                    )
                    
                    # Metin döndüyse, manuel bir kelime-zamanlama yapısı oluştur
                    if basic_transcript:
                        text = str(basic_transcript)
                        
                        # FFmpeg ile ses dosyasının süresini öğren
                        try:
                            import subprocess
                            ffprobe_cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{audio_path}"'
                            result = subprocess.run(ffprobe_cmd, shell=True, capture_output=True, text=True)
                            duration = float(result.stdout.strip())
                        except Exception:
                            # Süre alınamazsa yaklaşık bir değer kullan
                            duration = 30.0  # Varsayılan 30 saniye
                        
                        # Manuel yapı oluştur (daha sonra subtitle_renderer.py'da işlenecek)
                        manual_transcript = {
                            "text": text,
                            "duration": duration,
                            "language": "tr",  # Varsayılan dil
                            "_manual": True    # Manuel oluşturulduğunu belirt
                        }
                        
                        return manual_transcript
        
        # Tüm denemeler başarısız olursa boş bir yanıt döndür
        return {"error": "Failed to transcribe audio with Whisper API"}
    except Exception as e:
        print(f"Whisper analiz hatası: {str(e)}")
        return {"error": str(e), "text": "", "duration": 0, "language": "tr"}

def save_word_timings(transcript: Dict[str, Any], output_path: str) -> bool:
    """
    Whisper API'den alınan kelime zamanlamalarını JSON dosyasına kaydeder
    
    Args:
        transcript (Dict[str, Any]): Whisper API'den alınan transkript
        output_path (str): Kaydedilecek JSON dosyasının yolu
    
    Returns:
        bool: Başarılı ise True, değilse False
    """
    try:
        # TranscriptionVerbose nesnesini dict'e dönüştür
        if hasattr(transcript, "model_dump"):
            # Pydantic v2 için
            transcript_dict = transcript.model_dump()
        elif hasattr(transcript, "dict"):
            # Pydantic v1 için
            transcript_dict = transcript.dict()
        else:
            # Nesne zaten dict ise
            transcript_dict = dict(transcript)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(transcript_dict, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Kelime zamanlamaları kaydetme hatası: {str(e)}")
        # Hata durumunda basit bir JSON oluştur
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump({"text": str(transcript), "words": []}, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

def generate_tts(sentences: List[str], api_key: str, voice: str, project_folder: str, language: str = "tr") -> List[str]:
    """
    Verilen metinleri TTS ile seslendirme dosyalarına dönüştürür
    
    Args:
        sentences (List[str]): Seslendirilecek cümleler
        api_key (str): OpenAI API anahtarı
        voice (str): Kullanılacak ses (örn. "onyx", "alloy")
        project_folder (str): Proje klasörünün yolu
        language (str): Seslendirme dili (default: "tr" için Türkçe)
    
    Returns:
        List[str]: Oluşturulan ses dosyalarının yolları
    """
    # TTS klasörünü oluştur
    tts_folder = os.path.join(project_folder, "tts_audio")
    os.makedirs(tts_folder, exist_ok=True)
    
    # Ses dosyalarının yollarını sakla
    audio_files = []
    
    try:
        # OpenAI client oluştur
        client = OpenAI(api_key=api_key)
        
        # Toplam TTS süresini sınırla - maksimum 60 saniye
        max_sentences = min(len(sentences), 10)  # Maximum 10 cümle kullan
        total_duration = 0
        max_total_duration = 60  # Maksimum 60 saniye
        
        # FFmpeg yolunu config.json'dan al (ses süresi hesaplaması için)
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        ffprobe_path = "ffprobe"
        
        # Config dosyasını kontrol et - güncel ses modeli için
        current_voice = voice  # Varsayılan olarak parametre değerini kullan
        
        # Config dosyasını kontrol et ve varsa güncel ses modelini al
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    
                    # FFprobe yolunu güncelle
                    if "ffprobe_path" in config:
                        ffprobe_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config["ffprobe_path"])
                    
                    # Ses modelini güncelle - config.json dosyasındaki değer öncelikli
                    if "default_tts_voice" in config:
                        current_voice = config.get("default_tts_voice")
                        print(f"TTS ses modeli config.json'dan güncellendi: '{voice}' -> '{current_voice}'")
            except Exception as e:
                print(f"Config okuma hatası: {str(e)}")
        
        for i, sentence in enumerate(sentences[:max_sentences]):
            # Ses dosyasının adı
            audio_path = os.path.join(tts_folder, f"audio_{i+1:02d}.mp3")
            
            # Temiz bir cümle hazırla ve sayıları yazıya çevir
            clean_sentence = sentence.strip()
            if not clean_sentence:
                continue
            
            # Sayıları yazıya çevir (1881 -> bin sekiz yüz seksen bir) - Türkçe içinse
            if language == "tr":
                clean_sentence = convert_numbers_to_text(clean_sentence)
            
            print(f"TTS için hazırlanan metin ({language}): {clean_sentence}")
            
            # TTS oluştur - hızı dile göre ayarla
            # Varsayılan hız 1.0, akıcı konuşma için 1.2
            voice_speed = 1.2
            
            # Dile özel ayarlar
            voice_options = {
                "tr": {"voice": current_voice, "speed": 1.2},
                "en": {"voice": current_voice, "speed": 1.0},
                "es": {"voice": current_voice, "speed": 1.1},
                "fr": {"voice": current_voice, "speed": 1.1},
                "de": {"voice": current_voice, "speed": 1.1},
                "it": {"voice": current_voice, "speed": 1.1},
                "pt": {"voice": current_voice, "speed": 1.1},
                "ru": {"voice": current_voice, "speed": 1.0},
                "zh": {"voice": current_voice, "speed": 0.9},
                "ja": {"voice": current_voice, "speed": 1.0},
                "ko": {"voice": current_voice, "speed": 1.0},
                "ar": {"voice": current_voice, "speed": 1.1}
            }
            
            # Dile göre ayarları al veya varsayılan kullan
            voice_config = voice_options.get(language, {"voice": current_voice, "speed": 1.0})
            
            # Kullanılan ses modelini log'la
            print(f"TTS kullanılan ses modeli: {voice_config['voice']}")
            
            # TTS oluştur
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice_config["voice"],
                input=clean_sentence,
                speed=voice_config["speed"]
            )
            
            # Tempfile ile geçici dosya oluştur
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_path = temp_file.name
                
                # İçeriği geçici dosyaya yaz
                response.stream_to_file(temp_path)
                
                # Ses süresini hesapla (ffprobe ile)
                try:
                    duration_cmd = f'"{ffprobe_path}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{temp_path}"'
                    result = subprocess.run(duration_cmd, shell=True, capture_output=True, text=True)
                    file_duration = float(result.stdout.strip())
                    
                    # Toplam süreyi kontrol et ve gerekirse döngüyü sonlandır
                    if total_duration + file_duration > max_total_duration:
                        print(f"TTS süresi sınırını ({max_total_duration} saniye) aştı, sonraki cümleler atlanıyor.")
                        break
                    
                    total_duration += file_duration
                except Exception as dur_error:
                    print(f"Ses süresi hesaplama hatası: {str(dur_error)}")
                
                # Geçici dosyayı kopyala
                shutil.copy2(temp_path, audio_path)
                
                # Temizle
                try:
                    os.unlink(temp_path)
                except:
                    pass
                
                # Ses dosyasını listeye ekle
                audio_files.append(audio_path)
                print(f"Ses dosyası oluşturuldu ({language}): {audio_path}")
                
                # Artık her ses dosyası için ayrı ayrı Whisper analizi yapmıyoruz
                # Bunun yerine tüm ses dosyalarını birleştirip tek bir analiz yapacağız
        
        # Ses dosyalarını birleştir
        merged_audio = os.path.join(tts_folder, "merged_audio.mp3")
        
        if len(audio_files) > 1:
            # FFmpeg yolunu config.json'dan al
            ffmpeg_path = "ffmpeg"
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                        if "ffmpeg_path" in config:
                            ffmpeg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config["ffmpeg_path"])
                except:
                    pass
            
            # Birleştirme için concat listesi oluştur
            concat_list_path = os.path.join(tts_folder, "concat_list.txt")
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for audio_file in audio_files:
                    f.write(f"file '{os.path.abspath(audio_file)}'\n")
            
            # Birleştirme komutu
            concat_cmd = f'"{ffmpeg_path}" -f concat -safe 0 -i "{os.path.abspath(concat_list_path)}" -c copy "{os.path.abspath(merged_audio)}"'
            
            try:
                print("Ses dosyaları birleştiriliyor...")
                subprocess.run(concat_cmd, shell=True, check=True)
                
                # Geçici dosyayı temizle
                if os.path.exists(concat_list_path):
                    os.remove(concat_list_path)
            except Exception as e:
                print(f"Ses birleştirme hatası: {str(e)}")
                # Hata durumunda ilk ses dosyasını kullan
                if len(audio_files) > 0:
                    shutil.copy2(audio_files[0], merged_audio)
                else:
                    # Boş ses dosyası oluştur
                    with open(merged_audio, 'wb') as f:
                        f.write(b'')
        elif len(audio_files) == 1:
            # Tek ses dosyası varsa kopyala
            shutil.copy2(audio_files[0], merged_audio)
        else:
            # Ses dosyası yoksa boş dosya oluştur
            with open(merged_audio, 'wb') as f:
                f.write(b'')
        
        # Birleştirilmiş ses dosyasını Whisper API ile analiz et
        if os.path.exists(merged_audio) and os.path.getsize(merged_audio) > 0:
            try:
                print("Birleştirilmiş ses dosyası Whisper API ile analiz ediliyor...")
                transcript = analyze_audio_with_whisper(merged_audio, api_key)
                
                # Kelime zamanlamalarını kaydet
                timing_path = os.path.join(tts_folder, "full_timing.json")
                save_word_timings(transcript, timing_path)
                print(f"Tam kelime zamanlamaları kaydedildi: {timing_path}")
            except Exception as whisper_error:
                print(f"Whisper analizi hatası: {str(whisper_error)}")
        
        return audio_files
        
    except Exception as e:
        print(f"TTS üretme hatası: {str(e)}")
        return audio_files  # Oluşturulan dosyaları döndür
