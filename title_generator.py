#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
from modules.topic_generator import generate_topics_batch, generate_topic, generate_english_topic

def load_config():
    """Loads the configuration file"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Hata: config.json dosyası okunamadı: {str(e)}")
        sys.exit(1)

def save_titles_to_file(titles, filename):
    """Başlıkları dosyaya kaydeder"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for i, title in enumerate(titles, 1):
                f.write(f"{i}. {title}\n")
        print(f"\nBaşlıklar başarıyla {filename} dosyasına kaydedildi.")
    except Exception as e:
        print(f"Hata: Dosya yazma hatası: {str(e)}")

def main():
    """Ana fonksiyon"""
    # Komut satırı argümanlarını tanımla
    parser = argparse.ArgumentParser(description='YouTube Shorts için viral başlık üretici')
    parser.add_argument('-c', '--count', type=int, default=15, help='Üretilecek başlık sayısı (varsayılan: 15)')
    parser.add_argument('-l', '--language', choices=['tr', 'en'], default='en', help='Başlık dili (tr: Türkçe, en: İngilizce, varsayılan: en)')
    parser.add_argument('-s', '--single', action='store_true', help='Tek başlık üret (varsayılan: toplu üretim)')
    parser.add_argument('-o', '--output', help='Başlıkları kaydetmek için dosya adı (isteğe bağlı)')
    
    # Argümanları işle
    args = parser.parse_args()
    
    try:
        # Konfigürasyon dosyasından API anahtarını al
        config = load_config()
        api_key = config.get("openai_api_key", "")
        
        if not api_key:
            print("Hata: OpenAI API anahtarı bulunamadı! config.json dosyasını kontrol edin.")
            sys.exit(1)
        
        # Başlıkları üret
        if args.single:
            # Tek başlık üret
            if args.language == 'en':
                title = generate_english_topic(api_key)
                print(f"\n{title}")
            else:
                title = generate_topic(api_key)
                print(f"\n{title}")
            
            # Dosyaya kaydet (isteğe bağlı)
            if args.output:
                save_titles_to_file([title], args.output)
        else:
            # Toplu başlık üretimi
            print(f"\n{args.count} adet {args.language.upper()} başlık üretiliyor...\n")
            is_english = args.language == 'en'
            
            if is_english:
                print("Generating titles in ENGLISH...")
            else:
                print("Başlıklar TÜRKÇE olarak üretiliyor...")
                
            titles = generate_topics_batch(api_key, count=args.count, english=is_english)
            
            # Başlıkları ekrana yazdır
            for i, title in enumerate(titles, 1):
                print(f"{i}. {title}")
            
            # Dosyaya kaydet (isteğe bağlı)
            if args.output:
                save_titles_to_file(titles, args.output)
    
    except KeyboardInterrupt:
        print("\nİşlem kullanıcı tarafından iptal edildi.")
        sys.exit(0)
    except Exception as e:
        print(f"Beklenmeyen hata: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 