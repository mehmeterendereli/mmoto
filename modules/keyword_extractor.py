#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import openai
from typing import List
import re

def extract_keywords(sentences: List[str], topic: str) -> List[str]:
    """
    Verilen cümlelerden anahtar kelimeleri çıkarır
    
    Args:
        sentences (List[str]): Anahtar kelimelerin çıkarılacağı cümleler
        topic (str): Ana konu
    
    Returns:
        List[str]: Anahtar kelimeler listesi
    """
    try:
        # Topic'ten doğrudan anahtar kelime çıkar
        topic_words = topic.split()
        
        # İngilizce veya Türkçe soru formatını temizle
        clean_topic = topic.replace("?", "").replace("!", "").replace(".", "")
        
        # İngilizce mi kontrol et
        is_english = any(word in topic.lower() for word in ["what", "why", "how", "if", "can", "do", "is", "are", "will", "would"]) or "?" in topic
        
        # İngilizce soru kelimelerini ve yaygın bağlaçları kaldır
        if is_english:
            stop_words = ["what", "why", "how", "is", "are", "if", "would", "will", "can", "do", "does", "did", "the", "a", "an", "in", "on", "at", "to", "from", "with", "about", "for", "of", "by", "so", "such", "this", "these", "those", "that"]
        else:
            # Türkçe soru kelimelerini ve yaygın bağlaçları kaldır
            stop_words = ["neden", "nasıl", "niçin", "ne", "nerede", "mi", "mı", "mu", "mü", "acaba", "hangi", "eğer", "ya", "ve", "veya", "ile", "için", "gibi", "da", "de", "ki", "bu", "şu", "o"]
        
        # Konu kelimelerini temizle ve önemli anahtar kelimeleri çıkar
        important_words = []
        for word in clean_topic.split():
            word = word.lower().strip()
            if word and len(word) > 2 and word not in stop_words:
                # İlk harfi büyüt
                important_words.append(word.capitalize())
        
        # İçerikten de bazı önemli kelimeleri çıkar
        content_text = " ".join(sentences)
        
        # Aynı kelimelerden kaçınmak için mevcut kelimeleri kontrol et
        existing_words = set(w.lower() for w in important_words)
        
        # İçerikten önemli kelimeleri bul
        for sentence in sentences:
            words = sentence.split()
            for word in words:
                # Noktalama işaretlerini kaldır
                word = re.sub(r'[^\w\s]', '', word).strip()
                
                # Kelimeyi değerlendir
                if word and len(word) > 3 and word.lower() not in existing_words and word.lower() not in stop_words:
                    # Büyük harfle başlayan veya tamamen büyük harfle yazılmış kelimeleri muhtemelen önemlidir
                    if word[0].isupper() or word.isupper():
                        important_words.append(word)
                        existing_words.add(word.lower())
        
        # Ana konuyu ilk anahtar kelime olarak ekle
        primary_keyword = None
        
        # Konudan ana anahtar kelimeyi bul
        if len(important_words) > 0:
            primary_keyword = important_words[0]
        elif len(clean_topic.split()) > 0:
            primary_keyword = clean_topic.split()[0].capitalize()
        else:
            primary_keyword = "Video"
        
        # Anahtar kelimeleri düzenle ve ana kelimeyi başa koy
        final_keywords = [primary_keyword]
        for word in important_words:
            if word != primary_keyword and word not in final_keywords:
                final_keywords.append(word)
        
        # Toplam anahtar kelime sayısını sınırla
        final_keywords = final_keywords[:5]  # En fazla 5 anahtar kelime
        
        # Anahtar kelimeleri yazdır
        print("Keywords:", ", ".join(final_keywords))
        
        return final_keywords
        
    except Exception as e:
        print(f"Anahtar kelime çıkarma hatası: {str(e)}")
        return [topic.split()[0] if topic and len(topic.split()) > 0 else "Video"]
