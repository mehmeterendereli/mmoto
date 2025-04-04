"""
Dil yönetimi modülü - MMoto uygulaması için çoklu dil desteği sağlar
"""

import importlib.util
import os
import sys

class LanguageManager:
    """
    Dil yöneticisi sınıfı - Çoklu dil desteği sağlar
    """
    def __init__(self, default_lang="tr"):
        """
        Dil yöneticisini başlatır
        
        Args:
            default_lang (str): Varsayılan dil kodu (tr veya en)
        """
        self.current_lang = default_lang
        self.langs = {}
        self.load_languages()
    
    def load(self):
        """
        Dil yöneticisini yeniden yükler
        Bu metod, LanguageManager'ın zaten yüklenmiş olduğu durumda, 
        dil dosyalarını tekrar yüklemek için çağrılabilir.
        """
        self.load_languages()
        return True
    
    def load_languages(self):
        """
        Kullanılabilir tüm dilleri yükler
        """
        # Dil dizinini kontrol et
        langs_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Tüm dil dosyalarını tara
        for lang_file in os.listdir(langs_dir):
            # Sadece Python dosyalarını işle
            if lang_file.endswith('.py') and lang_file != '__init__.py' and lang_file != 'language_manager.py':
                lang_code = lang_file.split('.')[0]  # Uzantısız dosya adı (dil kodu)
                
                try:
                    # Dil modülünü dinamik olarak yükle
                    spec = importlib.util.spec_from_file_location(
                        f"langs.{lang_code}", 
                        os.path.join(langs_dir, lang_file)
                    )
                    lang_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(lang_module)
                    
                    # Dil sözlüğünü kaydet
                    if hasattr(lang_module, 'LANG'):
                        self.langs[lang_code] = lang_module.LANG
                except Exception as e:
                    print(f"Dil dosyası yüklenirken hata: {lang_file} - {str(e)}")
    
    def set_language(self, lang_code):
        """
        Geçerli dili değiştirir
        
        Args:
            lang_code (str): Dil kodu
        
        Returns:
            bool: Başarı durumu
        """
        if lang_code in self.langs:
            self.current_lang = lang_code
            return True
        return False
    
    def get(self, key, default=None):
        """
        Verilen anahtar için mevcut dildeki çeviriyi döndürür
        
        Args:
            key (str): Dil anahtarı
            default (str, optional): Anahtar bulunamazsa kullanılacak varsayılan değer

        Returns:
            str: Çeviri metni
        """
        # Geçerli dilde anahtarı ara
        if self.current_lang in self.langs and key in self.langs[self.current_lang]:
            return self.langs[self.current_lang][key]
        
        # Varsayılan değeri döndür
        if default:
            return default
            
        # Anahtarın kendisini döndür
        return key
    
    def get_languages(self):
        """
        Mevcut tüm dil kodlarını döndürür
        
        Returns:
            list: Dil kodları listesi
        """
        return list(self.langs.keys())
    
    def get_language(self):
        """
        Şu anda kullanılan dil kodunu döndürür
        
        Returns:
            str: Dil kodu
        """
        return self.current_lang

# Tek örnek (singleton) oluştur
language_manager = LanguageManager()

# Kolay erişim için yardımcı fonksiyon
def get_text(key, default=None):
    """
    Bir dil anahtarı için geçerli dildeki çeviriyi döndürür
    
    Args:
        key (str): Dil anahtarı
        default (str, optional): Anahtar bulunamazsa kullanılacak varsayılan değer
        
    Returns:
        str: Çeviri metni
    """
    return language_manager.get(key, default)

# Kısaltma tanımla
_ = get_text 