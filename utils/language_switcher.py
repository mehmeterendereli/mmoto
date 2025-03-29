#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
from typing import Dict, Any, List

class LanguageSwitcher:
    """Farklı dil destekleri için dil geçişi yönetimi sınıfı"""
    
    # Desteklenen diller
    SUPPORTED_LANGUAGES = {
        "TR": {
            "name": "Türkçe",
            "tts_voice": "onyx",
            "font_path": "assets/fonts/Montserrat-Bold.ttf"
        },
        "EN": {
            "name": "English",
            "tts_voice": "nova",
            "font_path": "assets/fonts/Montserrat-Bold.ttf"
        },
        "FR": {
            "name": "Français",
            "tts_voice": "alloy",
            "font_path": "assets/fonts/Montserrat-Bold.ttf"
        },
        "AR": {
            "name": "العربية",
            "tts_voice": "shimmer",
            "font_path": "assets/fonts/Montserrat-Bold.ttf"
        }
    }
    
    def __init__(self, default_language: str = "TR"):
        """
        Dil değiştirici sınıfını başlatır
        
        Args:
            default_language (str): Varsayılan dil kodu
        """
        if default_language not in self.SUPPORTED_LANGUAGES:
            default_language = "TR"
        
        self.current_language = default_language
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Konfigürasyon dosyasını yükler
        
        Returns:
            Dict[str, Any]: Konfigürasyon bilgileri
        """
        if not os.path.exists("config.json"):
            return {}
        
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _save_config(self) -> None:
        """Konfigürasyon dosyasına güncel ayarları kaydeder"""
        if not self.config:
            return
        
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def switch_language(self, language_code: str) -> bool:
        """
        Sistemin dilini değiştirir
        
        Args:
            language_code (str): Hedef dil kodu
        
        Returns:
            bool: Başarılı ise True, başarısız ise False
        """
        if language_code not in self.SUPPORTED_LANGUAGES:
            print(f"Hata: '{language_code}' desteklenen bir dil değil.")
            return False
        
        # Dili değiştir
        self.current_language = language_code
        
        # Konfigürasyon dosyasını güncelle
        if self.config:
            # TTS sesini güncelle
            self.config["default_tts_voice"] = self.SUPPORTED_LANGUAGES[language_code]["tts_voice"]
            
            # Font dosyasını güncelle
            self.config["font_path"] = self.SUPPORTED_LANGUAGES[language_code]["font_path"]
            
            # Değişiklikleri kaydet
            self._save_config()
        
        print(f"Dil başarıyla değiştirildi: {self.SUPPORTED_LANGUAGES[language_code]['name']}")
        return True
    
    def translate_prompt(self, prompt: str, target_language: str = None) -> str:
        """
        Verilen bir promptu hedef dile çevirir
        
        Args:
            prompt (str): Çevrilecek prompt
            target_language (str): Hedef dil kodu
        
        Returns:
            str: Çevrilmiş prompt
        """
        target_language = target_language or self.current_language
        
        if target_language not in self.SUPPORTED_LANGUAGES:
            return prompt
        
        # Dil çevirisi için OpenAI kullan
        try:
            import openai
            
            if not self.config.get("openai_api_key"):
                print("Uyarı: OpenAI API anahtarı bulunamadı. Çeviri yapılamıyor.")
                return prompt
            
            client = openai.OpenAI(api_key=self.config["openai_api_key"])
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"Sen profesyonel bir çevirmensin. Verilen metni {self.SUPPORTED_LANGUAGES[target_language]['name']} diline çevir. Çevirinin doğal dilde olması önemli."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            translated_prompt = response.choices[0].message.content
            return translated_prompt
            
        except Exception as e:
            print(f"Çeviri hatası: {str(e)}")
            return prompt
    
    def get_available_languages(self) -> List[Dict[str, str]]:
        """
        Kullanılabilir dillerin listesini döndürür
        
        Returns:
            List[Dict[str, str]]: Dil kodu ve adı içeren nesneler listesi
        """
        return [
            {"code": code, "name": info["name"]} 
            for code, info in self.SUPPORTED_LANGUAGES.items()
        ]
        
    def get_current_language(self) -> Dict[str, str]:
        """
        Mevcut dili döndürür
        
        Returns:
            Dict[str, str]: Mevcut dil bilgisi
        """
        return {
            "code": self.current_language,
            "name": self.SUPPORTED_LANGUAGES[self.current_language]["name"],
            "tts_voice": self.SUPPORTED_LANGUAGES[self.current_language]["tts_voice"]
        } 