"""
Dil ile ilgili yardımcı fonksiyonlar ve sabitler
"""

# Desteklenen diller
SUPPORTED_LANGUAGES = {
    "tr": "lang_tr",
    "en": "lang_en",
    "es": "lang_es",
    "fr": "lang_fr",
    "de": "lang_de",
    "it": "lang_it",
    "pt": "lang_pt",
    "ru": "lang_ru",
    "zh": "lang_zh",
    "ja": "lang_ja",
    "ko": "lang_ko",
    "ar": "lang_ar"
}

# Varsayılan diller
DEFAULT_UI_LANGUAGE = "tr"
DEFAULT_CONTENT_LANGUAGE = "tr"
DEFAULT_TTS_LANGUAGE = "tr"
DEFAULT_SUBTITLE_LANGUAGE = "tr"

def get_language_name(language_code, translate_func):
    """
    Dil kodundan dil adını döndürür
    
    Args:
        language_code (str): Dil kodu (tr, en, es vs.)
        translate_func (callable): Çeviri fonksiyonu
        
    Returns:
        str: Dil adı (yerelleştirilmiş)
    """
    lang_key = SUPPORTED_LANGUAGES.get(language_code)
    if lang_key:
        return translate_func(lang_key)
    return language_code

def get_language_options(translate_func):
    """
    Tüm desteklenen dillerin listesini döndürür
    
    Args:
        translate_func (callable): Çeviri fonksiyonu
        
    Returns:
        list: (dil_kodu, yerelleştirilmiş_dil_adı) çiftlerinden oluşan liste
    """
    options = []
    
    for code, key in SUPPORTED_LANGUAGES.items():
        name = translate_func(key)
        options.append((code, name))
    
    return options 