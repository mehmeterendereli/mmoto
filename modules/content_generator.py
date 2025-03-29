#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import openai
from openai import OpenAI
import re
from typing import Dict, Any

def generate_content(topic: str) -> Dict[str, Any]:
    """
    Verilen konu için bilgi içerikli metin üretir
    
    Args:
        topic (str): İçerik konusu
    
    Returns:
        Dict[str, Any]: Üretilen içerik bilgileri
    """
    # Konfigürasyon dosyasından OpenAI API anahtarını al
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    api_key = ""
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                api_key = config.get("openai_api_key", "")
        except:
            pass
    
    if not api_key:
        print("Uyarı: OpenAI API anahtarı bulunamadı!")
        # Dummy içerik döndür
        return {
            "topic": topic,
            "response": [
                "Bu bir örnek içeriktir.",
                f"{topic} hakkında bilgi bulunamadı.",
                "Lütfen API anahtarınızı kontrol edin."
            ]
        }
    
    try:
        # OpenAI istemcisini başlat
        client = OpenAI(api_key=api_key)
        
        # GPT-4o sistemi kullanarak içerik üret
        prompt = f"""
        Bana {topic} hakkında kısa, bilgilendirici bir metin yaz. 
        Bu metin bir video için TTS ile seslendirilecek.
        
        Önemli Kurallar:
        1. Metin konuya direkt olarak girmeli, "merhaba, bugün... konusunu anlatacağım" gibi gereksiz giriş cümleleri olmamalı
        2. Her cümle ayrı bir paragraf olmalı, listelemeler ve numaralandırmalar olmamalı
        3. Toplam 7 cümle olmalı ve tüm metin seslendirildiğinde yaklaşık 45 saniye sürmelidir (ASLA 50 saniyeyi geçmemeli)
        4. Her cümle anlamlı ve öğretici olmalı
        5. Metin hedef kitlesi genel izleyici, yani teknik olmayan bir dil kullan
        6. Her cümle 12-20 kelime arasında olmalı ve Türkçe olmalı
        7. Metin sadece düz cümlelerden oluşmalı, sadece 7 cümlelik bir metin olmalı
        8. Her cümle 2-4 saniye arası bir nefes alma süresi içermeli (doğallık için)
        
        Lütfen tamamen yukarıdaki kurallara uygun, toplam 7 cümlelik ve TTS okunduğunda toplam 35-45 saniye arası sürecek bir metin oluştur.
        Her cümleyi ayrı bir paragraf olarak ver.
        """
        
        # İstek gönder
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Sen kısa, bilgilendirici içerik üreten bir asistansın."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Cevabı al ve işle
        content = response.choices[0].message.content
        
        # Cevabı cümlelere ayır - her bir paragraf bir cümle olacak
        sentences = []
        for paragraph in content.strip().split('\n'):
            paragraph = paragraph.strip()
            if paragraph:  # Boş paragrafları atla
                # Madde işaretleri ve numaralar varsa kaldır
                cleaned = re.sub(r'^\d+\.\s*|\*\s*|\-\s*', '', paragraph)
                sentences.append(cleaned)
        
        # Cümle sayısını kontrol et ve gerekirse düzenle
        if len(sentences) > 7:
            sentences = sentences[:7]  # Maksimum 7 cümle
        
        # Sonuçları döndür
        return {
            "topic": topic,
            "response": sentences
        }
    
    except Exception as e:
        print(f"İçerik üretme hatası: {str(e)}")
        # Hata durumunda dummy içerik döndür
        return {
            "topic": topic,
            "response": [
                f"{topic} hakkında içerik oluşturulurken bir hata oluştu.",
                "API ile iletişimde sorun yaşandı.",
                "Lütfen daha sonra tekrar deneyiniz."
            ]
        } 