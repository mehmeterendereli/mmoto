#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import openai
from openai import OpenAI
from typing import List, Dict, Any
import re

def extract_keywords(sentences: List[str], topic: str, language: str = "tr", openai_api_key: str = "") -> List[str]:
    """
    Verilen cümlelerden anahtar kelimeleri çıkarır
    
    Args:
        sentences (List[str]): Anahtar kelimelerin çıkarılacağı cümleler
        topic (str): Ana konu
        language (str): İçerik dili (default: "tr")
        openai_api_key (str): OpenAI API anahtarı (varsa)
    
    Returns:
        List[str]: Anahtar kelimeler listesi
    """
    # OpenAI API varsa, daha akıllı anahtar kelime çıkarma
    if openai_api_key:
        try:
            return extract_keywords_with_openai(sentences, topic, language, openai_api_key)
        except Exception as e:
            print(f"OpenAI ile anahtar kelime çıkarma hatası: {str(e)}")
            # Hata durumunda basit metoda dön
            
    # Basit anahtar kelime çıkarma yöntemi
    try:
        # Topic'ten doğrudan anahtar kelime çıkar
        clean_topic = topic.replace("?", "").replace("!", "").replace(".", "")
        
        # Dile göre durak kelimelerini (stop words) belirle
        stop_words = get_stop_words(language)
        
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
        print(f"Keywords ({language}): {', '.join(final_keywords)}")
        
        return final_keywords
        
    except Exception as e:
        print(f"Anahtar kelime çıkarma hatası: {str(e)}")
        return [topic.split()[0] if topic and len(topic.split()) > 0 else "Video"]

def extract_keywords_with_openai(sentences: List[str], topic: str, language: str, api_key: str) -> List[str]:
    """
    OpenAI API kullanarak daha akıllı anahtar kelime çıkarma
    
    Args:
        sentences (List[str]): Anahtar kelimelerin çıkarılacağı cümleler
        topic (str): Ana konu
        language (str): İçerik dili
        api_key (str): OpenAI API anahtarı
    
    Returns:
        List[str]: Anahtar kelimeler listesi (her zaman İngilizce)
    """
    # OpenAI istemcisi oluştur
    client = OpenAI(api_key=api_key)
    
    # Dil adını getir
    language_names = {
        "tr": "Turkish",
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "ar": "Arabic"
    }
    lang_name = language_names.get(language, "English")
    
    # Metni hazırla
    content_text = "\n".join(sentences)
    
    # GPT Prompt hazırla - her zaman İngilizce anahtar kelimeler iste
    prompt = f"""
    Extract 5 most important search keywords from the following {lang_name} content and translate them to English. 
    These keywords will be used to search for relevant stock videos in Pexels.
    
    Topic: {topic}
    
    Content:
    {content_text}
    
    Rules:
    1. Extract exactly 5 most relevant keywords that would help find good video footage
    2. First keyword should be the most important one (main subject)
    3. Keywords should be single words, not phrases
    4. Each keyword should start with a capital letter
    5. Return keywords as a comma-separated list only, no explanations or numbering
    6. Focus on concrete visual objects that would appear in videos
    7. IMPORTANT: Keywords MUST be in English, regardless of the source language
    
    Keywords:
    """
    
    # API isteği gönder
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You extract the most relevant visual keywords from content and translate them to English."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=100
        )
        
        # Yanıtı işle
        keywords_text = response.choices[0].message.content.strip()
        
        # Virgülle ayrılmış anahtar kelimeleri listeye çevir
        keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
        
        # Boş liste durumunda basit yönteme geri dön
        if not keywords:
            return extract_keywords(sentences, topic, language)
        
        # En fazla 5 anahtar kelime
        keywords = keywords[:5]
        
        print(f"OpenAI Keywords ({language}): {', '.join(keywords)}")
        
        return keywords
        
    except Exception as e:
        print(f"Çeviri hatası: {str(e)}")
        # Hata durumunda orijinal kelimeleri döndür
        return extract_keywords(sentences, topic, language)

def get_stop_words(language: str) -> List[str]:
    """
    Belirtilen dil için durak kelimelerini (stop words) döndürür
    
    Args:
        language (str): Dil kodu (örn. "tr", "en")
    
    Returns:
        List[str]: Durak kelimeleri listesi
    """
    stop_words = {
        "tr": [
            "neden", "nasıl", "niçin", "ne", "nerede", "mi", "mı", "mu", "mü", 
            "acaba", "hangi", "eğer", "ya", "ve", "veya", "ile", "için", "gibi", 
            "da", "de", "ki", "bu", "şu", "o", "bir", "ise", "ama", "fakat", 
            "olarak", "kadar", "kez", "defa", "kere", "aslında", "sonra", "önce"
        ],
        "en": [
            "what", "why", "how", "is", "are", "if", "would", "will", "can", 
            "do", "does", "did", "the", "a", "an", "in", "on", "at", "to", 
            "from", "with", "about", "for", "of", "by", "so", "such", "this", 
            "these", "those", "that", "as", "but", "or", "and", "then", "than",
            "when", "where", "which", "who", "whom", "whose"
        ],
        "es": [
            "qué", "por qué", "cómo", "es", "son", "si", "puede", "el", "la", 
            "los", "las", "un", "una", "unos", "unas", "con", "sin", "de", "en", 
            "por", "para", "como", "y", "o", "pero", "porque", "donde", "cuando",
            "quien", "cuyo", "cuya", "este", "esta", "estos", "estas"
        ],
        "fr": [
            "pourquoi", "comment", "est", "sont", "si", "peut", "le", "la", 
            "les", "un", "une", "des", "avec", "sans", "de", "en", "par", 
            "pour", "comme", "et", "ou", "mais", "parce", "où", "quand",
            "qui", "que", "ce", "cette", "ces"
        ],
        "de": [
            "warum", "wie", "ist", "sind", "wenn", "kann", "der", "die", 
            "das", "ein", "eine", "mit", "ohne", "von", "in", "für", 
            "als", "und", "oder", "aber", "weil", "wo", "wann",
            "wer", "was", "dieser", "diese", "dieses"
        ]
    }
    
    # Dil için durak kelimeleri yoksa İngilizce durak kelimelerini döndür
    return stop_words.get(language, stop_words["en"])
