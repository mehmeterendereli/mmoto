"""
Türkçe dil dosyası
"""

LANG = {
    # Ana arayüz öğeleri
    "app_title": "MMoto Video Oluşturucu",
    "ready": "Hazır",
    "working": "Çalışıyor...",
    "error": "Hata",
    
    # Menü
    "home": "Ana Sayfa",
    "api_keys": "API Anahtarları",
    "settings": "Ayarlar",
    "appearance": "Görünüm:",
    
    # Ana sayfa
    "topic": "Konu:",
    "generate_topic": "Konu Oluştur",
    "log_title": "İşlem Günlüğü:",
    "continuous_mode": "Sürekli Çalışma Modu",
    "language": "Dil:",
    "turkish": "Türkçe",
    "english": "İngilizce",
    "max_videos": "Maksimum Video Sayısı:",
    "status": "Durum:",
    "start": "Başlat",
    "stop": "Durdur",
    "check_youtube": "YouTube Ayarlarını Kontrol Et",
    
    # Ayarlar sayfası
    "ui_language": "Arayüz Dili:",
    "content_language": "İçerik Dili:",
    "tts_language": "Seslendirme Dili:",
    "subtitle_language": "Altyazı Dili:",
    "content_and_tts_language": "İçerik ve Seslendirme Dili:",
    "content_language_info": "Seçilen arayüz dili sadece arayüzün dilini belirler ve videoları etkilemez. İçerik dili, videoların hangi dilde oluşturulacağını belirler. İçerik ve seslendirme dilleri genellikle aynı olmalıdır, ancak altyazı dilini farklı bir dilde seçebilirsiniz. Değişikliklerinizin etkili olması için lütfen 'Ayarları Kaydet' butonuna tıklayın.",
    "select_language": "Dil Seçin",
    
    # Desteklenen diller
    "lang_tr": "Türkçe",
    "lang_en": "İngilizce",
    "lang_es": "İspanyolca",
    "lang_fr": "Fransızca",
    "lang_de": "Almanca",
    "lang_it": "İtalyanca",
    "lang_pt": "Portekizce",
    "lang_ru": "Rusça",
    "lang_zh": "Çince",
    "lang_ja": "Japonca",
    "lang_ko": "Korece",
    "lang_ar": "Arapça",
    
    # API Anahtarları sayfası
    "api_title": "API Anahtarları",
    "openai_api": "OpenAI API Key:",
    "pexels_api": "Pexels API Key:",
    "youtube_api": "YouTube API Key:",
    "pixabay_api": "Pixabay API Key:",
    "show_keys": "API Anahtarlarını Göster",
    "save_settings": "Ayarları Kaydet",
    "settings_saved": "Ayarlar başarıyla kaydedildi!",
    
    # İşlem mesajları
    "process_started": "İşlem başlatıldı",
    "process_completed": "İşlem tamamlandı",
    "process_stopped": "İşlem durduruldu",
    "continuous_mode_enabled": "Sürekli çalışma modu etkinleştirildi",
    "continuous_mode_disabled": "Sürekli çalışma modu devre dışı bırakıldı",
    "new_topic_generated": "Yeni konu oluşturuldu",
    "auto_generating_topic": "Konu otomatik olarak oluşturuluyor...",
    "preparing_next_video": "Bir sonraki video için hazırlanıyor...",
    "content_language_changed": "İçerik dili değiştirildi",
    "content_and_tts_language_changed": "İçerik ve seslendirme dili değiştirildi",
    "tts_language_changed": "Seslendirme dili değiştirildi",
    "subtitle_language_changed": "Altyazı dili değiştirildi",
    "warning_default_language": "İçerik dili belirtilmediği için varsayılan dil kullanılıyor",
    "warning_tts_language_set": "Seslendirme dili içerik dili ile aynı olarak ayarlandı",
    "warning_subtitle_language_set": "Altyazı dili içerik dili ile aynı olarak ayarlandı",
    "using_content_language": "Kullanılan içerik dili",
    "using_content_and_tts_language": "Kullanılan içerik ve seslendirme dili",
    "using_tts_language": "Kullanılan seslendirme dili",
    "using_subtitle_language": "Kullanılan altyazı dili",
    
    # YouTube ayarları
    "youtube_settings_ok": "YouTube ayarları kontrol edildi ve sorun bulunamadı",
    "error_no_youtube_key": "YouTube API anahtarı bulunamadı",
    "error_no_client_secrets": "client_secrets.json dosyası bulunamadı",
    "youtube_setup_instructions": "YouTube API'yi kullanabilmek için client_secrets.json dosyasını oluşturmanız gerekmektedir. Detaylı bilgi için Google Cloud Console'a gidin.",
    
    # Hata mesajları
    "error_no_topic": "Lütfen bir konu girin veya oluşturun",
    "error_already_running": "İşlem zaten çalışıyor",
    "error_no_openai_key": "OpenAI API anahtarı bulunamadı",
    "error_during_process": "İşlem sırasında hata oluştu",
    
    # Yardım başlıkları
    "openai_help_title": "OpenAI API Key Nasıl Alınır",
    "pexels_help_title": "Pexels API Key Nasıl Alınır",
    "youtube_help_title": "YouTube API Key Nasıl Alınır",
    "pixabay_help_title": "Pixabay API Key Nasıl Alınır",
    
    # Yardım içerikleri
    "openai_help_content": "OpenAI API Key almak için şu adımları izleyin:\n\n"
                          "1. OpenAI hesabınıza giriş yapın (yoksa kaydolun)\n"
                          "2. Sağ üst köşedeki profil menüsüne tıklayın\n"
                          "3. 'View API Keys' seçeneğini seçin\n"
                          "4. 'Create new secret key' butonuna tıklayın\n"
                          "5. Oluşturulan anahtarı kopyalayın ve bu alana yapıştırın\n\n"
                          "NOT: API anahtarınız 'sk-...' ile başlar ve yaklaşık 50 karakter uzunluğundadır.",
    
    "pexels_help_content": "Pexels API Key almak için şu adımları izleyin:\n\n"
                          "1. Pexels hesabınıza giriş yapın (yoksa kaydolun)\n"
                          "2. https://www.pexels.com/api/new/ adresine gidin\n"
                          "3. 'Your API Key' bölümünden anahtarınızı kopyalayın\n"
                          "4. Kopyaladığınız anahtarı bu alana yapıştırın\n\n"
                          "NOT: Pexels API anahtarı yaklaşık 30-40 karakter uzunluğundadır.",
    
    "youtube_help_content": "YouTube API Key almak için şu adımları izleyin:\n\n"
                            "1. Google Cloud Console'a giriş yapın\n"
                            "2. Bir proje oluşturun (yoksa)\n"
                            "3. API Kütüphanesi'nden YouTube Data API v3'ü etkinleştirin\n"
                            "4. Kimlik Bilgileri menüsünden API anahtarı oluşturun\n"
                            "5. Oluşturulan anahtarı bu alana yapıştırın\n\n"
                            "NOT: YouTube API anahtarı 'AIzaSy...' ile başlar.",
    
    "pixabay_help_content": "Pixabay API Key almak için şu adımları izleyin:\n\n"
                           "1. Pixabay hesabınıza giriş yapın (yoksa kaydolun)\n"
                           "2. https://pixabay.com/api/docs/ adresine gidin\n"
                           "3. Sayfanın alt tarafındaki 'API Key Request' bölümünü doldurun\n"
                           "4. Onay e-postasıyla aldığınız API anahtarını bu alana yapıştırın\n\n"
                           "NOT: Pixabay API anahtarı 15-20 karakter uzunluğunda rakam ve harflerden oluşur.",
    
    # Yardım bağlantıları
    "openai_help_link": "OpenAI API Keys Sayfasına Git",
    "pexels_help_link": "Pexels API Sayfasına Git",
    "youtube_help_link": "Google Cloud Console'a Git",
    "pixabay_help_link": "Pixabay API Sayfasına Git",
    
    # Diğer
    "close": "Kapat",
    "error_prefix": "Hata: "
} 