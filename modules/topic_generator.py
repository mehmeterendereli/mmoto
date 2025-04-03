#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import random
from openai import OpenAI
import logging
import re

# Üretilen konuları saklamak için dosya yolu
TOPICS_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stats", "topics_history.json")

def load_topics_history():
    """
    Daha önce üretilmiş konu geçmişini yükler
    
    Returns:
        list: Daha önce üretilmiş konuların listesi
    """
    if not os.path.exists(TOPICS_HISTORY_FILE):
        # Dosya yoksa, stats klasörünü oluştur ve boş bir liste döndür
        os.makedirs(os.path.dirname(TOPICS_HISTORY_FILE), exist_ok=True)
        with open(TOPICS_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    
    try:
        with open(TOPICS_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Konu geçmişi yüklenirken hata: {str(e)}")
        return []

def save_topic_to_history(topic):
    """
    Üretilen konuyu geçmiş listesine ekler
    
    Args:
        topic (str): Eklenecek konu
    """
    try:
        topics = load_topics_history()
        if topic not in topics:
            topics.append(topic)
            with open(TOPICS_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(topics, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"Konu geçmişi kaydedilirken hata: {str(e)}")

def generate_topic(api_key, category=None):
    """
    GPT-4o API kullanarak özgün bir konu üretir
    
    Args:
        api_key (str): OpenAI API anahtarı
        category (str, optional): Konu kategorisi. Belirtilmezse rastgele kategori seçilir.
    
    Returns:
        str: Üretilen konu
    """
    # Daha önce üretilmiş konuları yükle
    previous_topics = load_topics_history()
    
    # Kategori seçimi
    categories = [
        "Bilim", "Tarih", "Teknoloji", "Doğa", "Uzay", "İlginç Bilgiler",
        "Hayvanlar", "Coğrafya", "Sanat", "Spor", "Sağlık", "Psikoloji",
        "İnsan Vücudu", "Yapay Zeka", "İcatlar", "Tuhaf Gerçekler"
    ]
    
    if not category:
        category = random.choice(categories)
    
    try:
        # OpenAI istemcisini başlat
        client = OpenAI(api_key=api_key)
        
        # Daha önce üretilmiş konular hakkında bilgi ver
        previous_topics_str = ", ".join(previous_topics[-10:]) if previous_topics else "Henüz konu üretilmedi"
        
        # GPT-4o ile konu üretimi - viral başlık formatında
        prompt = f"""
        Act as a viral YouTube Shorts content strategist for a Turkish channel named "Merak Makinesi". Generate an engaging, curiosity-driven video title using viral language and relevant emojis.

        Use formats like:
        - "Ya... olsaydı?" (What If...)
        - "Neden...?" (Why...)
        - "Nasıl...?" (How...)
        - "İşte bu yüzden..." (This Is Why...)
        - "İnanamayacaksın..." (You Won't Believe...)
        - "Arkasındaki Sır..." (The Secret Behind...)
        
        The title should be between 5-10 words, include at least 1-2 emojis related to the topic, and be optimized to grab attention in YouTube Shorts.
        
        Category: {category}
        
        Important Rules:
        1. Title should be in Turkish
        2. Must be clickable and spark curiosity
        3. Should be short and catchy (5-10 words)
        4. Must include 1-2 relevant emojis
        5. Should focus on trending or evergreen topics
        6. Should not be similar to these previous titles: {previous_topics_str}
        7. Question format works well (e.g. "Dünya Dönmeyi Durdurursa Ne Olur? 🌍💥")
        
        Output only the title, no explanation or additional text.
        """
        
        # API isteği
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Sen viral YouTube Shorts başlıkları üreten bir uzmansın. Başlık üretirken emoji kullanmayı unutma."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=100
        )
        
        # Yanıtı al ve temizle
        topic = response.choices[0].message.content.strip()
        
        # Başında veya sonunda gereksiz karakterler varsa temizle
        topic = topic.strip('"\'.,;:!?')
        
        # Konuyu geçmişe kaydet
        save_topic_to_history(topic)
        
        return topic
        
    except Exception as e:
        logging.error(f"Konu üretme hatası: {str(e)}")
        
        # Hata durumunda varsayılan konular
        default_topics = [
            "Dünya Dönmeyi Durdurursa Ne Olur? 🌍💥",
            "İşte Bu Yüzden Rüya Görüyorsun 🧠💤",
            "Evren Ne Kadar Büyük? 🌌😱",
            "Ağaçların Gizli Dili 🌳🗣️",
            "Uçaklar Neden Pasifik Okyanusundan Kaçınır? ✈️🌊",
            "Ay Bir Gün Yok Olursa Ne Olur? 🌕🚫",
            "Yapay Zeka Gerçekten Düşünebilir Mi? 🤖🧠",
            "Neden Çocukluk Anılarımızı Unutuyoruz? 👶🧠",
            "Dinozorlar Hala Yaşasaydı Ne Olurdu? 🦖🌍",
            "Dünyanın En Derin Deliği 🌍🕳️",
            "Neden Tüylerimiz Diken Diken Olur? 😨🧬",
            "Kara Deliklerde Ne Olur? 🕳️💫",
            "Piramitler Hakkında Gerçekler 🏜️🔺"
        ]
        
        # Daha önce kullanılmamış bir konu seç
        for topic in default_topics:
            if topic not in previous_topics:
                save_topic_to_history(topic)
                return topic
        
        # Hepsi kullanılmışsa rastgele bir tane seç
        topic = random.choice(default_topics)
        return topic

def generate_english_topic(api_key, category=None):
    """
    GPT-4o API kullanarak İngilizce viral YouTube Shorts başlığı üretir
    
    Args:
        api_key (str): OpenAI API anahtarı
        category (str, optional): Konu kategorisi. Belirtilmezse rastgele kategori seçilir.
    
    Returns:
        str: Üretilen İngilizce başlık
    """
    # Kategori seçimi
    categories = [
        "Science", "History", "Technology", "Nature", "Space", "Interesting Facts",
        "Animals", "Geography", "Art", "Sports", "Health", "Psychology",
        "Human Body", "AI", "Inventions", "Strange Facts"
    ]
    
    if not category:
        category = random.choice(categories)
    
    try:
        # OpenAI istemcisini başlat
        client = OpenAI(api_key=api_key)
        
        # GPT-4o ile konu üretimi - viral başlık formatında (İngilizce)
        prompt = f"""
        Act as a viral YouTube Shorts content strategist for a channel named "Curiosity Machine". Generate an engaging, curiosity-driven video title using viral language and relevant emojis.

        Use formats like:
        - "What If..."
        - "Why..."
        - "How..."
        - "This Is Why..."
        - "You Won't Believe..."
        - "The Secret Behind..."
        
        The title should be between 5-10 words, include at least 1-2 emojis related to the topic, and be optimized to grab attention in YouTube Shorts or TikTok feeds.
        
        Category: {category}
        
        IMPORTANT RULES:
        1. Must be clickable and spark curiosity
        2. Should be short and catchy (5-10 words)
        3. Must include 1-2 relevant emojis
        4. Should focus on trending or evergreen topics
        5. Question format works well (e.g. "What If Earth Stopped Spinning? 🌍💥")
        6. TITLE MUST BE IN ENGLISH ONLY
        
        Output only the title, no explanation or additional text.
        """
        
        # API isteği
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert at creating viral YouTube Shorts titles IN ENGLISH ONLY. Always use emojis in your titles and never switch to another language."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=100
        )
        
        # Yanıtı al ve temizle
        topic = response.choices[0].message.content.strip()
        
        # Başında veya sonunda gereksiz karakterler varsa temizle
        topic = topic.strip('"\'.,;:!?')
        
        return topic
        
    except Exception as e:
        logging.error(f"İngilizce başlık üretme hatası: {str(e)}")
        
        # Hata durumunda varsayılan İngilizce konular
        default_topics = [
            "What If Earth Stopped Spinning? 🌍💥",
            "This Is Why You Dream 🧠💤",
            "How Big Is the Universe? 🌌😱",
            "The Secret Language of Trees 🌳🗣️",
            "Why Airplanes Avoid the Pacific Ocean ✈️🌊",
            "What If the Moon Disappeared? 🌕🚫",
            "Can AI Really Think? 🤖🧠",
            "Why Do We Forget Our Childhood? 👶🧠",
            "What If Dinosaurs Still Existed? 🦖🌍",
            "The Deepest Hole on Earth 🌍🕳️",
            "Why Do We Get Goosebumps? 😨🧬",
            "What Happens in a Black Hole? 🕳️💫",
            "The Truth About the Pyramids 🏜️🔺",
            "How Animals See the World 👁️🐾",
            "The Mystery of Bermuda Triangle 🌊🔺"
        ]
        
        # Rastgele bir başlık seç
        topic = random.choice(default_topics)
        return topic

def generate_topics_batch(api_key, count=15, english=True):
    """
    Birden fazla başlık üretir (toplu üretim)
    
    Args:
        api_key (str): OpenAI API anahtarı
        count (int): Üretilecek başlık sayısı
        english (bool): True ise İngilizce, False ise Türkçe başlıklar üretir
    
    Returns:
        list: Üretilen başlıkların listesi
    """
    # Kategori listesi
    categories_en = [
        "Science", "History", "Technology", "Nature", "Space", 
        "Psychology", "Human Body", "AI", "Inventions", "Strange Facts"
    ]
    
    categories_tr = [
        "Bilim", "Tarih", "Teknoloji", "Doğa", "Uzay", 
        "Psikoloji", "İnsan Vücudu", "Yapay Zeka", "İcatlar", "Tuhaf Gerçekler"
    ]
    
    try:
        # OpenAI istemcisini başlat
        client = OpenAI(api_key=api_key)
        
        if english:
            # İngilizce toplu başlık üretimi için prompt
            prompt = """
            Act as a viral YouTube Shorts content strategist for a channel named "Curiosity Machine". Generate 15 short, engaging, and curiosity-driven video titles using viral language and relevant emojis.

            Use formats like:
            - "What If..."
            - "Why..."
            - "How..."
            - "This Is Why..."
            - "You Won't Believe..."
            - "The Secret Behind..."

            Each title should be between 5–10 words, include at least 1–2 emojis related to the topic, and be optimized to grab attention in YouTube Shorts or TikTok feeds.

            Topic themes: science, space, psychology, technology, biology, ancient history, nature, human body, AI, inventions, and strange facts.

            IMPORTANT: ALL TITLES MUST BE IN ENGLISH ONLY. DO NOT USE ANY OTHER LANGUAGE.

            Output only the titles, in this format:
            1. [Title with Emoji]
            2. ...
            """
            
            # API isteği
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert at creating viral YouTube Shorts titles in ENGLISH ONLY. Always use emojis in your titles and never switch to another language."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                max_tokens=1000
            )
        else:
            # Türkçe toplu başlık üretimi için prompt
            prompt = """
            Bir viral YouTube Shorts içerik stratejisti olarak "Merak Makinesi" adlı bir kanal için çalış. Viral dil ve ilgili emojileri kullanarak 15 kısa, ilgi çekici ve merak uyandıran video başlığı üret.

            Şu formatları kullan:
            - "Ya... olsaydı?"
            - "Neden...?"
            - "Nasıl...?"
            - "İşte bu yüzden..."
            - "İnanamayacaksın..."
            - "Arkasındaki Sır..."

            Her başlık 5-10 kelime arasında olmalı, konuyla ilgili en az 1-2 emoji içermeli ve YouTube Shorts veya TikTok akışlarında dikkat çekmek için optimize edilmelidir.

            Konu temaları: bilim, uzay, psikoloji, teknoloji, biyoloji, antik tarih, doğa, insan vücudu, yapay zeka, icatlar ve tuhaf gerçekler.

            Sadece başlıkları şu formatta çıktı olarak ver:
            1. [Emojili Başlık]
            2. ...
            """
            
            # Türkçe API isteği
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Sen viral YouTube Shorts başlıkları üreten bir uzmansın. Başlık üretirken emoji kullanmayı unutma. Tüm başlıklar sadece Türkçe olmalı."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                max_tokens=1000
            )
        
        # Yanıtı al
        content = response.choices[0].message.content.strip()
        
        # Yanıtı işle - satır satır ayır ve numaraları kaldır
        lines = content.split('\n')
        titles = []
        
        for line in lines:
            # Sadece numaralı satırları işle (1., 2. gibi)
            if re.match(r'^\d+\.', line.strip()):
                # Numarayı kaldır
                title = re.sub(r'^\d+\.\s*', '', line.strip())
                # Temizle
                title = title.strip('"\'.,;:!? ')
                if title:
                    titles.append(title)
        
        # İstenen sayıda başlık döndür
        return titles[:count]
        
    except Exception as e:
        logging.error(f"Toplu başlık üretme hatası: {str(e)}")
        
        # Hata durumunda varsayılan başlıklar
        if english:
            default_topics = [
                "What If Earth Stopped Spinning? 🌍💥",
                "This Is Why You Dream 🧠💤",
                "How Big Is the Universe? 🌌😱",
                "The Secret Language of Trees 🌳🗣️",
                "Why Airplanes Avoid the Pacific Ocean ✈️🌊",
                "What If the Moon Disappeared? 🌕🚫",
                "Can AI Really Think? 🤖🧠",
                "Why Do We Forget Our Childhood? 👶🧠",
                "What If Dinosaurs Still Existed? 🦖🌍",
                "The Deepest Hole on Earth 🌍🕳️",
                "Why Do We Get Goosebumps? 😨🧬",
                "What Happens in a Black Hole? 🕳️💫",
                "The Truth About the Pyramids 🏜️🔺",
                "How Animals See the World 👁️🐾",
                "The Mystery of Bermuda Triangle 🌊🔺"
            ]
        else:
            default_topics = [
                "Dünya Dönmeyi Durdurursa Ne Olur? 🌍💥",
                "İşte Bu Yüzden Rüya Görüyorsun 🧠💤",
                "Evren Ne Kadar Büyük? 🌌😱",
                "Ağaçların Gizli Dili 🌳🗣️",
                "Uçaklar Neden Pasifik Okyanusundan Kaçınır? ✈️🌊",
                "Ay Bir Gün Yok Olursa Ne Olur? 🌕🚫",
                "Yapay Zeka Gerçekten Düşünebilir Mi? 🤖🧠",
                "Neden Çocukluk Anılarımızı Unutuyoruz? 👶🧠",
                "Dinozorlar Hala Yaşasaydı Ne Olurdu? 🦖🌍",
                "Dünyanın En Derin Deliği 🌍🕳️",
                "Neden Tüylerimiz Diken Diken Olur? 😨🧬",
                "Kara Deliklerde Ne Olur? 🕳️💫",
                "Piramitler Hakkında Gerçekler 🏜️🔺",
                "Hayvanlar Dünyayı Nasıl Görür? 👁️🐾",
                "Bermuda Üçgeni'nin Gizemi 🌊🔺"
            ]
        
        # İstenen sayıda rastgele başlık döndür
        random.shuffle(default_topics)
        return default_topics[:count]

# Test için
if __name__ == "__main__":
    # config.json'dan API anahtarını al
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    api_key = ""
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                api_key = config.get("openai_api_key", "")
        except:
            pass
    
    if api_key:
        print("======= Türkçe Başlık =======")
        topic = generate_topic(api_key)
        print(f"Üretilen konu: {topic}")
        
        print("\n======= İngilizce Başlık =======")
        eng_topic = generate_english_topic(api_key)
        print(f"Generated topic: {eng_topic}")
        
        print("\n======= Toplu Başlık Üretimi (İngilizce) =======")
        topics = generate_topics_batch(api_key, count=15, english=True)
        for i, topic in enumerate(topics, 1):
            print(f"{i}. {topic}")
    else:
        print("API anahtarı bulunamadı!") 