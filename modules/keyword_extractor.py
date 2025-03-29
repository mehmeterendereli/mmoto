#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import openai
from typing import List

def extract_keywords(sentences: List[str], topic: str = "") -> List[str]:
    """
    Verilen metinden video araması için anahtar kelimeleri çıkarır
    
    Args:
        sentences (List[str]): İçerik metni (cümleler listesi)
        topic (str, optional): Ana konu. Varsayılan değer boş string.
    
    Returns:
        List[str]: Video araması için anahtar kelimeler
    """
    try:
        # Cümleleri tek bir metne birleştir
        full_text = " ".join(sentences)
        
        # OpenAI API anahtarını kontrol et
        import json
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                api_key = config.get("openai_api_key", "")
        else:
            api_key = ""
            
        if not api_key or len(api_key) < 10:
            print("OpenAI API anahtarı bulunamadı, basit anahtar kelime çıkarma kullanılacak")
            # Basit kelime çıkarma kullan
            import re
            words = re.findall(r'\b\w{5,}\b', full_text.lower())
            unique_words = list(set(words))
            # En sık geçen 5 kelimeyi al
            word_count = {}
            for word in words:
                word_count[word] = word_count.get(word, 0) + 1
            
            sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
            keywords = [word for word, count in sorted_words[:5]]
        else:
            # GPT-4o kullanarak anahtar kelimeleri çıkart
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Sen bir metin analisti ve anahtar kelime çıkarıcısısın."},
                    {"role": "user", "content": f"""Aşağıdaki metinden Pexels API'de video arama yapmak için 3 adet anahtar kelime çıkar. 
                    
Önemli kurallar:
1. Anahtar kelimeler basit ve net olmalı (örneğin: ocean, fish, underwater)
2. Bileşik terimler KULLANMA, sadece tek kelimeler kullan
3. Çok genel terimlerden kaçın (nature, landscape gibi)
4. Metindeki görsel öğelere odaklan
5. Anahtar kelimeler İngilizce olmalı
6. Her anahtar kelime tek bir satırda olmalı

Metin: {full_text}
Konu: {topic}"""}
                ]
            )
            
            # Yanıtı satırlara böl
            text = response.choices[0].message.content
            keywords = [line.strip() for line in text.split('\n') if line.strip()]
            
            # En fazla 3 anahtar kelime al (API limitini azaltmak için)
            keywords = keywords[:3]
        
        # Anahtar kelimeleri dosyaya kaydet
        project_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_folder = os.path.join(project_folder, "output")
        
        # En son oluşturulan klasörü bul
        folders = [f for f in os.listdir(output_folder) if os.path.isdir(os.path.join(output_folder, f))]
        if folders:
            latest_folder = max(folders, key=lambda x: os.path.getctime(os.path.join(output_folder, x)))
            project_folder = os.path.join(output_folder, latest_folder)
            
            with open(os.path.join(project_folder, "pexels_keywords.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(keywords))
            
            print(f"Anahtar kelimeler: {', '.join(keywords)}")
        
        return keywords
    
    except Exception as e:
        print(f"Anahtar kelime çıkarma hatası: {str(e)}")
        # Hata durumunda varsayılan anahtar kelimeler
        keywords = ["landscape", "nature", "education"]
        print(f"Varsayılan anahtar kelimeler kullanılıyor: {', '.join(keywords)}")
        return keywords
