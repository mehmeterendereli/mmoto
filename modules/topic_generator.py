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
    GPT-4o API kullanarak viral YouTube Shorts başlığı üretir
    
    Args:
        api_key (str): OpenAI API anahtarı
        category (str, optional): Konu kategorisi. Belirtilmezse rastgele kategori seçilir.
    
    Returns:
        str: Üretilen başlık
    """
    # Kategori seçimi
    categories = [
        "Bilim", "Tarih", "Teknoloji", "Doğa", "Uzay", "İlginç Bilgiler",
        "Hayvanlar", "Coğrafya", "Sanat", "Spor", "Sağlık", "Psikoloji",
        "İnsan Vücudu", "Yapay Zeka", "İcatlar", "Tuhaf Gerçekler"
    ]
    
    if not category:
        category = random.choice(categories)
    
    # Daha önce kullanılmış başlıkları kontrol et (tekrarları önlemek için)
    previous_topics = []
    stats_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stats")
    topics_file = os.path.join(stats_folder, "topics.json")
    
    if os.path.exists(topics_file):
        try:
            with open(topics_file, "r", encoding="utf-8") as f:
                previous_topics = json.load(f)
        except:
            previous_topics = []
    
    # Son 20 başlığı al (çok uzunsa)
    previous_topics_str = ", ".join(previous_topics[-20:]) if previous_topics else "Henüz başlık yok"
    
    try:
        # OpenAI istemcisini başlat
        client = OpenAI(api_key=api_key)
        
        # GPT-4o ile konu üretimi - viral başlık formatında
        prompt = f"""
        Sen viral YouTube Shorts ve TikTok başlıkları üreten bir uzmansın. "Merak Makinesi" isimli bir Türkçe kanal için en yüksek tıklama oranına sahip olacak başlıklar üretmekle görevlisin.

        MÜKEMMEL BİR YOUTUBE SHORTS BAŞLIĞI ÜRET.

        BAŞLIK KRİTERLERİ:
        1. ZORUNLU: "🤯" veya "😱" içeren ŞOK EDİCİ bir başlık olmalı
        2. Başlıkta mutlaka BÜYÜK HARFLER kullanılmalı
        3. Başlık izleyiciyi HEMEN tıklatacak kadar merak uyandırmalı
        4. Şu kelimelerden birini içermeli: "İNANILMAZ", "ŞOKE", "SIR", "GİZLİ", "YASAKLI", veya "İMKANSIZ"
        5. Şu formatlardan birini kullan (ama tam olarak kopyalama, sadece ilham al):
           - "HERKES ŞOKTA! [konu] Hakkında İNANILMAZ Gerçek! 😱"
           - "KİMSE BİLMİYORDU! [konu] Hakkındaki GİZLİ SIR! 🤯"
           - "BAKMAYI BIRAKAMAYACAKSIN! [konu] Nasıl [şaşırtıcı şey yapıyor]? 😱"
           - "EĞER [konu] Hakkında Bunu Bilmiyorsan HER ŞEYİ YANLIŞ Yapıyorsun! 🤯"
           - "BİLİM İNSANLARI ŞOK! [konu] Aslında [beklenmedik durum]... 😱"
        6. Toplam 5-10 kelime arasında olmalı
        7. Başlık %100 Türkçe olmalı
        8. Kategori: {category}
        9. Daha önce benzer başlıklar kullanılmamalı
        10. İnsanların HEMEN tıklamak isteyeceği kadar merak uyandırıcı olmalı
        
        SADECE KLİCKBAİT BAŞLIĞI YAZ, ek açıklama veya metin ekleme.
        """
        
        # API isteği
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Sen viral YouTube Shorts başlıkları üreten bir uzmansın. Başlık üretirken emoji kullanmayı asla unutma. Başlıklar çok şok edici olmalı."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=100
        )
        
        # Yanıtı al ve temizle
        topic = response.choices[0].message.content.strip()
        
        # Başında veya sonunda gereksiz karakterler varsa temizle
        topic = topic.strip('"\'.,;:!?')
        
        # Üretilen konuyu kaydet
        if os.path.exists(stats_folder):
            if topic not in previous_topics:
                previous_topics.append(topic)
                try:
                    with open(topics_file, "w", encoding="utf-8") as f:
                        json.dump(previous_topics, f, ensure_ascii=False, indent=4)
                except:
                    pass
        
        print(f"Üretilen başlık: {topic}")
        
        return topic
        
    except Exception as e:
        print(f"Başlık üretimi hatası: {str(e)}")
        return f"Bilgilendirici Videolar: {category}"

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

def generate_topic_international(api_key, language="es", category=None):
    """
    GPT-4o API kullanarak farklı dillerde özgün bir konu üretir
    
    Args:
        api_key (str): OpenAI API anahtarı
        language (str): Hedef dil kodu ("es", "fr", "de" vb.)
        category (str, optional): Konu kategorisi. Belirtilmezse rastgele kategori seçilir.
    
    Returns:
        str: Üretilen konu
    """
    # Dil adını ayarla
    lang_names = {
        "es": "Spanish",
        "fr": "French", 
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese", 
        "ru": "Russian",
        "ar": "Arabic"
    }
    lang_name = lang_names.get(language, "Spanish")  # Varsayılan İspanyolca
    
    # Kategori seçimi - İngilizce kategorileri kullan
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
        
        # Dile özel formatlar
        title_formats = {
            "es": [
                "Qué Pasaría Si...",
                "Por Qué...",
                "Cómo...",
                "Esta Es La Razón...",
                "No Creerás...",
                "El Secreto Detrás De..."
            ],
            "fr": [
                "Que Se Passerait-il Si...",
                "Pourquoi...",
                "Comment...",
                "Voici Pourquoi...",
                "Vous Ne Croirez Pas...",
                "Le Secret Derrière..."
            ],
            "de": [
                "Was Wäre Wenn...",
                "Warum...",
                "Wie...",
                "Darum...",
                "Du Wirst Nicht Glauben...",
                "Das Geheimnis Hinter..."
            ]
        }
        
        # Varsayılan formatlar (dil listede yoksa)
        default_formats = [
            "What If...",
            "Why...",
            "How...",
            "This Is Why...",
            "You Won't Believe...",
            "The Secret Behind..."
        ]
        
        # Dile göre formatları al
        formats = title_formats.get(language, default_formats)
        formats_text = "\n".join([f"- {f}" for f in formats])
        
        # GPT-4o ile konu üretimi - viral başlık formatında (hedef dilde)
        prompt = f"""
        Act as a viral YouTube Shorts content strategist for a {lang_name} channel.
        Generate an engaging, curiosity-driven video title using viral language and relevant emojis.
        
        Use formats like:
        {formats_text}
        
        The title should:
        1. Be COMPLETELY in {lang_name} ONLY
        2. Include 1-2 relevant emojis
        3. Be short and catchy (5-10 words)
        4. Use question format if possible
        5. Spark curiosity
        
        Category: {category}
        
        Output only the title in {lang_name}, no explanations or additional text.
        """
        
        # API isteği
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"You are an expert at creating viral YouTube Shorts titles in {lang_name} ONLY. Always include emojis in your titles. NEVER use any other language than {lang_name}."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=100
        )
        
        # Yanıtı al ve temizle
        topic = response.choices[0].message.content.strip()
        
        # Başında veya sonunda gereksiz karakterler varsa temizle
        topic = topic.strip('"\'.,;:!?')
        
        # Log ekle
        print(f"Üretilen {lang_name} başlık: {topic}")
        
        return topic
        
    except Exception as e:
        logging.error(f"Konu üretme hatası ({lang_name}): {str(e)}")
        
        # Hata durumunda varsayılan konular (dile göre)
        default_topics = {
            "es": [
                "¿Qué Pasaría Si La Tierra Dejara De Girar? 🌍💥",
                "¿Por Qué Soñamos? 🧠💤",
                "El Secreto Detrás De Las Pirámides 🏜️🔺",
                "¿Pueden Pensar Los Robots? 🤖🧠"
            ],
            "fr": [
                "Que Se Passerait-il Si La Terre Arrêtait De Tourner? 🌍💥",
                "Pourquoi Rêvons-nous? 🧠💤",
                "Le Secret Derrière Les Pyramides 🏜️🔺",
                "Les Robots Peuvent-ils Penser? 🤖🧠"
            ],
            "de": [
                "Was Wäre Wenn Die Erde Aufhören Würde Sich Zu Drehen? 🌍💥",
                "Warum Träumen Wir? 🧠💤",
                "Das Geheimnis Hinter Den Pyramiden 🏜️🔺",
                "Können Roboter Denken? 🤖🧠"
            ]
        }
        
        # Dile göre varsayılan konuları seç, yoksa İspanyolca konuları kullan
        topics_list = default_topics.get(language, default_topics["es"])
        topic = random.choice(topics_list)
        
        return topic

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