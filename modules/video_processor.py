#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import random
import json
import shutil
from typing import List, Tuple

def process_videos(video_paths: List[str], resolution: Tuple[int, int], project_folder: str) -> str:
    """
    İndirilen videoları işler ve 9:16 formatına uygun hale getirir
    Her videodan maksimum 10 saniye alarak çeşitliliği artırır
    Ana konuyla ilgili videoları öncelikli olarak seçer
    
    Args:
        video_paths (List[str]): İşlenecek video dosyalarının yolları
        resolution (Tuple[int, int]): Hedef çözünürlük (genişlik, yükseklik)
        project_folder (str): Proje klasörünün yolu
    
    Returns:
        str: İşlenmiş video dosyasının yolu
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
    
    if not video_paths:
        print("Uyarı: İşlenecek video bulunamadı!")
        # Bir örnek video dosyası oluştur
        create_empty_video(project_folder, resolution, ffmpeg_path)
        return os.path.join(project_folder, "processed_video.mp4")
    
    try:
        # Anahtar kelime öncelikli video seçimi
        # Video dosya adlarından anahtar kelimeleri çıkar
        keyword_videos = {}
        primary_keyword = None
        
        for video_path in video_paths:
            # Dosya adından anahtar kelimeyi çıkar (video_Keyword_1.mp4 formatı)
            filename = os.path.basename(video_path)
            parts = filename.split('_')
            
            if len(parts) >= 3 and parts[0] == "video":
                keyword = parts[1]
                
                # Anahtar kelimeye göre videoları grupla
                if keyword not in keyword_videos:
                    keyword_videos[keyword] = []
                
                keyword_videos[keyword].append(video_path)
                
                # İlk karşılaşılan anahtar kelimeyi ana konu olarak kabul et
                if primary_keyword is None:
                    primary_keyword = keyword
        
        print(f"Bulunan anahtar kelimeler: {list(keyword_videos.keys())}")
        print(f"Ana konu: {primary_keyword}")
        
        # Anahtar kelime bazlı pexels_keywords.txt dosyasını kontrol et
        keywords_file = os.path.join(project_folder, "pexels_keywords.txt")
        if os.path.exists(keywords_file):
            try:
                with open(keywords_file, "r", encoding="utf-8") as f:
                    file_keywords = [line.strip() for line in f.readlines()]
                    if file_keywords:
                        # İlk anahtar kelimeyi ana konu olarak kabul et
                        primary_keyword = file_keywords[0]
                        print(f"pexels_keywords.txt'den ana konu: {primary_keyword}")
            except Exception as e:
                print(f"pexels_keywords.txt okuma hatası: {str(e)}")
        
        # Seçilecek videoları belirle
        selected_videos = []
        max_videos = 10  # Toplam maksimum video sayısı
        primary_video_count = 4  # Ana konudan seçilecek minimum video sayısı
        
        # Önce ana konuyla ilgili videoları ekle
        if primary_keyword and primary_keyword in keyword_videos:
            primary_videos = keyword_videos[primary_keyword]
            # Ana konu videolarını karıştır
            random.shuffle(primary_videos)
            # Ana konudan minimum sayıda video seç
            selected_count = min(len(primary_videos), primary_video_count)
            selected_videos.extend(primary_videos[:selected_count])
            print(f"Ana konu '{primary_keyword}'dan {selected_count} video seçildi")
        
        # Kalan boşlukları diğer anahtar kelimelerle doldur
        remaining_slots = max_videos - len(selected_videos)
        other_keywords = [k for k in keyword_videos.keys() if k != primary_keyword]
        
        if other_keywords and remaining_slots > 0:
            # Her anahtar kelimeden eşit sayıda video seç
            videos_per_keyword = remaining_slots // len(other_keywords)
            if videos_per_keyword == 0:
                videos_per_keyword = 1
            
            for keyword in other_keywords:
                if len(selected_videos) >= max_videos:
                    break
                    
                videos = keyword_videos[keyword]
                random.shuffle(videos)
                # Bu anahtar kelimeden seçilecek video sayısı
                to_select = min(len(videos), videos_per_keyword, max_videos - len(selected_videos))
                selected_videos.extend(videos[:to_select])
                print(f"'{keyword}' anahtar kelimesinden {to_select} video seçildi")
        
        # Hala boş slot varsa, kalan videoları ekle
        if len(selected_videos) < max_videos:
            remaining_videos = [v for v in video_paths if v not in selected_videos]
            random.shuffle(remaining_videos)
            remaining_count = min(len(remaining_videos), max_videos - len(selected_videos))
            selected_videos.extend(remaining_videos[:remaining_count])
            print(f"Kalan boşluklar için {remaining_count} video daha seçildi")
        
        print(f"Toplam {len(selected_videos)} video seçildi")
        
        # İşlenmiş videoların yollarını ve sürelerini sakla
        processed_videos = []
        total_duration = 0
        max_duration = 60  # Maksimum 60 saniye
        
        # Video sayısına göre süre hesapla
        total_videos = len(selected_videos)
        # Video sayısı arttıkça süreyi azalt, azaldıkça artır
        # 5 video veya daha az: 10 saniye
        # 15 video veya daha fazla: 5 saniye
        # Aradaki değerler için doğrusal interpolasyon
        if total_videos <= 5:
            max_clip_duration = 10.0
        elif total_videos >= 15:
            max_clip_duration = 5.0
        else:
            # 5 ile 15 video arasında doğrusal interpolasyon
            max_clip_duration = 10.0 - (total_videos - 5) * (5.0 / 10.0)
        
        print(f"Video sayısı: {total_videos}, her video için maksimum süre: {max_clip_duration:.2f} saniye")
        
        # Her videoyu dönüştür
        for i, video_path in enumerate(selected_videos):
            if not os.path.exists(video_path):
                print(f"Video dosyası bulunamadı: {video_path}")
                continue
            
            # Video boyutlarını al
            try:
                probe_cmd = f'"{ffprobe_path}" -v error -select_streams v:0 -show_entries stream=width,height -of json "{video_path}"'
                result = subprocess.run(probe_cmd, shell=True, capture_output=True, text=True)
                info = json.loads(result.stdout)
                width = int(info["streams"][0]["width"])
                height = int(info["streams"][0]["height"])
                
                # Video süresini al
                duration_cmd = f'"{ffprobe_path}" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
                result = subprocess.run(duration_cmd, shell=True, capture_output=True, text=True)
                original_duration = float(result.stdout.strip())
                
                # Video sayısına göre hesaplanan maksimum süreyi kullan
                clip_duration = min(original_duration, max_clip_duration)
                
                # Eğer video 10 saniyeden uzunsa, ortasından 10 saniye al
                if original_duration > 10.0:
                    # Videonun ortasından başla
                    start_time = (original_duration - clip_duration) / 2
                else:
                    # Kısa videolarda baştan başla
                    start_time = 0
                
                # Toplam süreyi kontrol et
                if total_duration + clip_duration > max_duration:
                    print(f"Toplam süre sınırına ulaşıldı ({max_duration} saniye), kalan videolar atlanıyor.")
                    break
                
                total_duration += clip_duration
                
            except Exception as e:
                print(f"Video bilgisi alınamadı veya dönüştürme hatası: {str(e)}")
                continue
            
            # Çıktı dosyasının yolu
            output_file = os.path.join(project_folder, f"scaled_video_{i+1}.mp4")
            
            # 9:16 dikey video için
            if resolution[0] / resolution[1] == 9/16:  # 9:16 formatı (dikey video)
                try:
                    # Videonun orijinal en-boy oranını koru, ancak 9:16 formatına uydur
                    if width / height > 9/16:  # Video daha geniş (tipik 16:9 formatı)
                        # Yeni yaklaşım: Video içeriğini 1:1 olarak al, üst ve alt kısımları bulanıklaştırılmış video ile doldur
                        # 1. Adım: Videoyu kare (1:1) formata kırp
                        square_size = min(width, height)
                        # Video genişse, en önemli içerik ortada olma ihtimali yüksek
                        x_offset = int((width - square_size) / 2)
                        y_offset = int((height - square_size) / 2)
                        
                        # 2. Adım: Orijinal videoyu bulanıklaştır ve 9:16 formata scale et
                        # 3. Adım: Kare kırpılmış videoyu 9:16 formatın ortasına yerleştir
                        # 4. Adım: SAR değerini 1:1 olarak ayarla
                        blur_cmd = f'"{ffmpeg_path}" -i "{video_path}" -ss {start_time:.2f} -t {clip_duration:.2f} -filter_complex ' + \
                                  f'"[0:v]crop={square_size}:{square_size}:{x_offset}:{y_offset},scale={resolution[0]}:{resolution[0]},setsar=1:1[fg]; ' + \
                                  f'[0:v]scale={resolution[0]}:{resolution[1]},boxblur=20:5,setsar=1:1[bg]; ' + \
                                  f'[bg][fg]overlay=(W-w)/2:({resolution[1]}-{resolution[0]})/2" ' + \
                                  f'-c:v libx264 -preset medium -crf 18 -profile:v high -pix_fmt yuv420p -r 30 -c:a aac -b:a 128k -y -b:v 5M -maxrate 5M -bufsize 5M "{output_file}"'
                        
                        crop_cmd = blur_cmd
                    else:  # Video daha dar veya tam 9:16, ölçeklendir
                        scale_cmd = f'"{ffmpeg_path}" -i "{video_path}" -ss {start_time:.2f} -t {clip_duration:.2f} -vf "scale={resolution[0]}:{resolution[1]},setsar=1:1" -c:v libx264 -preset medium -crf 18 -profile:v high -pix_fmt yuv420p -r 30 -c:a aac -b:a 128k -y -b:v 5M -maxrate 5M -bufsize 5M "{output_file}"'
                        crop_cmd = scale_cmd
                    
                    print(f"Video işleniyor ({i+1}/{len(selected_videos)}): {video_path}")
                    print(f"Kırpma: {start_time:.2f} saniyeden başlayarak {clip_duration:.2f} saniye")
                    subprocess.run(crop_cmd, shell=True, check=True)
                    
                    # İşlemi kontrol et
                    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                        processed_videos.append((output_file, clip_duration))
                        print(f"Video başarıyla işlendi: {output_file}, Süre: {clip_duration:.2f} saniye")
                    else:
                        print(f"Video işlenemedi: {output_file}")
                except Exception as e:
                    print(f"Video işleme hatası: {str(e)}")
            else:
                print(f"Desteklenmeyen çözünürlük: {resolution}, 9:16 formatı gerekli")
        
        if not processed_videos:
            raise ValueError("İşlenebilir video bulunamadı")
        
        # Toplam video süresini hesapla
        total_duration = sum(duration for _, duration in processed_videos)
        print(f"Toplam video süresi: {total_duration:.2f} saniye")
        
        # Eğer toplam süre maksimum süreden fazlaysa, bazı videoları çıkar
        if total_duration > max_duration:
            print(f"Toplam süre çok uzun ({total_duration:.2f} > {max_duration} saniye), bazı videolar çıkarılacak...")
            while processed_videos and total_duration > max_duration:
                # En uzun videoyu çıkar
                processed_videos.sort(key=lambda x: x[1], reverse=True)
                removed_video, removed_duration = processed_videos.pop(0)
                total_duration -= removed_duration
                print(f"Video çıkarıldı: {removed_video}, Yeni toplam süre: {total_duration:.2f} saniye")
        
        # Videoları birleştir
        if len(processed_videos) > 1:
            # Videoları birleştirmek için input listesi oluştur
            concat_list_path = os.path.join(project_folder, "video_concat_list.txt")
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for video_path, _ in processed_videos:
                    f.write(f"file '{os.path.abspath(video_path)}'\n")
            
            # Birleştirilmiş video yolu
            processed_video_path = os.path.join(project_folder, "processed_video.mp4")
            
            # SAR değerini 1:1 olarak ayarla
            concat_cmd = f'"{ffmpeg_path}" -f concat -safe 0 -i "{concat_list_path}" -vf "setsar=1:1" -c:v libx264 -preset medium -crf 20 -profile:v high -pix_fmt yuv420p -r 30 -vsync cfr -b:v 5M -maxrate 5M -bufsize 5M "{processed_video_path}"'
            
            try:
                print("Videolar birleştiriliyor...")
                print(f"Birleştirme komutu: {concat_cmd}")
                subprocess.run(concat_cmd, shell=True, check=True)
                
                # Geçici dosyaları temizleme
                try:
                    os.remove(concat_list_path)
                except Exception as e:
                    print(f"Video birleştirme hatası: {str(e)}")
                
                if os.path.exists(processed_video_path) and os.path.getsize(processed_video_path) > 0:
                    print(f"Videolar başarıyla birleştirildi: {processed_video_path}")
                    return processed_video_path
                else:
                    # Başarısız olursa ilk videoyu döndür
                    return processed_videos[0][0]
            except Exception as e:
                print(f"Video birleştirme hatası: {str(e)}")
                # Hata durumunda ilk videoyu döndür
                return processed_videos[0][0]
        elif len(processed_videos) == 1:
            # Tek video varsa işlenmiş video yolu
            processed_video_path = os.path.join(project_folder, "processed_video.mp4")
            video_path, _ = processed_videos[0]
            
            # SAR değerini 1:1 olarak ayarla
            sar_cmd = f'"{ffmpeg_path}" -i "{video_path}" -vf "setsar=1:1" -c:v libx264 -preset medium -crf 20 -profile:v high -pix_fmt yuv420p -r 30 -b:v 5M -maxrate 5M -bufsize 5M "{processed_video_path}"'
            subprocess.run(sar_cmd, shell=True, check=True)
            
            return processed_video_path
        else:
            raise ValueError("Hiç video işlenemedi")
    
    except Exception as e:
        print(f"Video işleme genel hatası: {str(e)}")
        # Hata durumunda boş bir video oluştur
        create_empty_video(project_folder, resolution, ffmpeg_path)
        return os.path.join(project_folder, "processed_video.mp4")

def create_empty_video(project_folder: str, resolution: Tuple[int, int], ffmpeg_path: str = "ffmpeg") -> None:
    """
    Boş bir video oluşturur (hata durumunda veya video bulunamadığında)
    
    Args:
        project_folder (str): Proje klasörünün yolu
        resolution (Tuple[int, int]): Video çözünürlüğü
        ffmpeg_path (str): FFmpeg uygulamasının yolu
    """
    try:
        output_path = os.path.join(project_folder, "processed_video.mp4")
        
        # Çözünürlüğü doğru şekilde formatla
        width, height = resolution
        if not isinstance(width, int) or not isinstance(height, int):
            width, height = 1080, 1920  # Varsayılan çözünürlük
        
        # 5 saniyelik siyah bir video oluştur
        cmd = f'"{ffmpeg_path}" -f lavfi -i color=c=black:s={width}x{height}:d=5 -c:v libx264 -pix_fmt yuv420p -r 30 "{os.path.abspath(output_path)}"'
        print(f"Boş video oluşturma komutu: {cmd}")
        
        subprocess.run(cmd, shell=True, check=True)
        
        print(f"Boş video oluşturuldu: {output_path}")
    except Exception as e:
        print(f"Boş video oluşturma hatası: {str(e)}")
        # Daha basit bir yöntem dene - bir örnek video dosyası kopayala
        try:
            # Örnek bir video dosyası varsa kopyala
            sample_video = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sample.mp4")
            if os.path.exists(sample_video):
                shutil.copy(sample_video, os.path.join(project_folder, "processed_video.mp4"))
                print(f"Örnek video kopyalandı: {sample_video}")
            else:
                # Başarısız olursa boş bir dosya oluştur
                with open(os.path.join(project_folder, "processed_video.mp4"), 'wb') as f:
                    f.write(b'')
        except Exception as e:
            print(f"Yedek video oluşturma hatası: {str(e)}")
            # Son çare olarak boş dosya oluştur
            try:
                with open(os.path.join(project_folder, "processed_video.mp4"), 'wb') as f:
                    f.write(b'')
            except:
                pass
