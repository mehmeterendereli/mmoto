import customtkinter as ctk
import threading
import asyncio
import json
import os
import sys
import queue
import webbrowser
from datetime import datetime
from PIL import Image, ImageTk
import time

# Ana programdan içe aktarmalar
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import process_single_video
from modules.topic_generator import generate_topic, generate_english_topic, generate_topic_international
from langs import language_manager, get_text, _  # Dil desteği için modül
from utils.language_utils import (
    SUPPORTED_LANGUAGES, 
    DEFAULT_UI_LANGUAGE, 
    DEFAULT_CONTENT_LANGUAGE, 
    DEFAULT_TTS_LANGUAGE, 
    DEFAULT_SUBTITLE_LANGUAGE,
    get_language_name,
    get_language_options
)

# Uygulama renkleri
APP_COLOR_PRIMARY = "#1f538d"
APP_COLOR_SECONDARY = "#14375e"
APP_COLOR_LIGHT = "#dedede"

class HelpPopup(ctk.CTkToplevel):
    """Yardım popup penceresi"""
    def __init__(self, parent, title, message, link=None, link_text=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("600x400")
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # İçerik
        header = ctk.CTkLabel(self, text=title, font=("Arial", 16, "bold"))
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        text_frame = ctk.CTkFrame(self)
        text_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        text_frame.grid_columnconfigure(0, weight=1)
        text_frame.grid_rowconfigure(0, weight=1)
        
        text = ctk.CTkTextbox(text_frame)
        text.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        text.insert("1.0", message)
        text.configure(state="disabled")
        
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=20, pady=20, sticky="ew")
        
        # Link butonu
        if link and link_text:
            link_button = ctk.CTkButton(
                button_frame, 
                text=link_text, 
                command=lambda: webbrowser.open(link)
            )
            link_button.pack(side="left", padx=10)
        
        # Kapat butonu
        close_button = ctk.CTkButton(
            button_frame, 
            text=_("close"), 
            command=self.destroy
        )
        close_button.pack(side="right", padx=10)

class MMotoApp(ctk.CTk):
    """Ana uygulama sınıfı"""
    def __init__(self):
        """Uygulamayı başlatır"""
        # Ana pencere (root) ayarları
        super().__init__()
        
        # Dil yöneticisini başlat
        language_manager.load()
        lang = language_manager.get_language()
        
        # Varsayılan dilleri ayarla
        DEFAULT_UI_LANGUAGE = "tr"  # Varsayılan dil: Türkçe
        DEFAULT_CONTENT_LANGUAGE = "tr"
        DEFAULT_SUBTITLE_LANGUAGE = "tr"
        
        # Ana değişkenleri başlat
        self.is_running = False  # İşlem çalışıyor mu?
        self.log_queue = queue.Queue()  # Log mesajları için kuyruk
        self.global_video_counter = 0  # Toplam üretilen video sayısı
        
        # Pencere ayarları
        self.title(_("app_title"))
        self.geometry("1000x650")
        self.minsize(800, 600)  # En küçük pencere boyutunu ayarla
        
        # Tema ayarı
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Değişkenler
        self.topic_var = ctk.StringVar()
        self.status_var = ctk.StringVar(value=_("ready"))
        self.continuous_var = ctk.BooleanVar(value=False)
        self.max_videos_var = ctk.StringVar(value="5")
        
        # Dil değişkenleri - varsayılan değerlerle başlatıyoruz
        self.ui_language_var = ctk.StringVar(value=DEFAULT_UI_LANGUAGE)
        self.content_language_var = ctk.StringVar(value=DEFAULT_CONTENT_LANGUAGE) 
        self.subtitle_language_var = ctk.StringVar(value=DEFAULT_SUBTITLE_LANGUAGE)
        
        # Geriye dönük uyumluluk için eski language_var'ı ui_language_var'a bağla
        self.language_var = self.ui_language_var
        
        self.current_page = "home"
        
        # API anahtarları değişkenleri
        self.openai_api_var = ctk.StringVar()
        self.pexels_api_var = ctk.StringVar()
        self.youtube_api_var = ctk.StringVar()
        self.pixabay_api_var = ctk.StringVar()
        
        # Ana düzen
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Menü ve içerik alanlarını oluştur
        self.create_sidebar()
        self.create_content_area()
        
        # Home sayfasını göster (başlangıç)
        self.show_home_page()
        
        # Log işleme zamanlayıcısı
        self.after(100, self.process_logs)
        
        # Ayarları yükle - Önce kontrolsüz kendiliğinden yüklemiyoruz
        self.add_log("Debug: Ayarlar yükleniyor...")
        config = self.load_config()
        
        # Dil değişikliği için olay bağlantısı
        self.ui_language_var.trace_add("write", self.on_language_change)
        
    def create_sidebar(self):
        """Sol taraftaki menü çubuğunu oluşturur"""
        # Menü çerçevesi
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=3, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        
        # Logo / Başlık
        logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="MMoto", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Menü butonları
        self.home_button = ctk.CTkButton(
            self.sidebar_frame, 
            text=_("home"),
            command=self.show_home_page
        )
        self.home_button.grid(row=1, column=0, padx=20, pady=10)
        
        self.api_button = ctk.CTkButton(
            self.sidebar_frame, 
            text=_("api_keys"),
            command=self.show_api_page
        )
        self.api_button.grid(row=2, column=0, padx=20, pady=10)
        
        # Ayarlar butonu
        self.settings_button = ctk.CTkButton(
            self.sidebar_frame, 
            text=_("settings"),
            command=self.show_settings_page
        )
        self.settings_button.grid(row=3, column=0, padx=20, pady=10)
        
        # Görünüm seçici (light/dark mode)
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text=_("appearance"), anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_menu = ctk.CTkOptionMenu(
            self.sidebar_frame, 
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode
        )
        self.appearance_mode_menu.grid(row=6, column=0, padx=20, pady=(10, 20))
        self.appearance_mode_menu.set("Dark")
    
    def create_content_area(self):
        """İçerik alanını oluşturur"""
        # Ana içerik alanı
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        # Sayfalar için frame'ler
        self.home_frame = ctk.CTkFrame(self.content_frame)
        self.api_frame = ctk.CTkFrame(self.content_frame)
        self.settings_frame = ctk.CTkFrame(self.content_frame)
        
        # Home Frame (Ana Sayfa)
        self.setup_home_frame()
        
        # API Keys Frame
        self.setup_api_frame()
        
        # Settings Frame (Ayarlar sayfası)
        self.setup_settings_frame()
    
    def change_appearance_mode(self, new_appearance_mode):
        """Görünüm modunu değiştirir"""
        ctk.set_appearance_mode(new_appearance_mode)
        
    def show_home_page(self):
        """Ana sayfayı gösterir"""
        self.current_page = "home"
        self.home_frame.pack(fill="both", expand=True)
        self.api_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.home_button.configure(fg_color=APP_COLOR_PRIMARY)
        self.api_button.configure(fg_color="transparent")
        self.settings_button.configure(fg_color="transparent")
        
    def show_api_page(self):
        """API Keys sayfasını gösterir"""
        self.current_page = "api"
        self.api_frame.pack(fill="both", expand=True)
        self.home_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.api_button.configure(fg_color=APP_COLOR_PRIMARY)
        self.home_button.configure(fg_color="transparent")
        self.settings_button.configure(fg_color="transparent")
        
    def show_settings_page(self):
        """Ayarlar sayfasını gösterir"""
        self.current_page = "settings"
        self.settings_frame.pack(fill="both", expand=True)
        self.home_frame.pack_forget()
        self.api_frame.pack_forget()
        self.settings_button.configure(fg_color=APP_COLOR_PRIMARY)
        self.home_button.configure(fg_color="transparent")
        self.api_button.configure(fg_color="transparent")
        
    def setup_home_frame(self):
        """Ana sayfa içeriğini oluşturur"""
        # Ana düzen
        self.home_frame.grid_columnconfigure(0, weight=1)
        self.home_frame.grid_rowconfigure(1, weight=1)
        
        # Üst panel - Konu girişi
        top_frame = ctk.CTkFrame(self.home_frame)
        top_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        top_frame.grid_columnconfigure(0, weight=0)
        top_frame.grid_columnconfigure(1, weight=1)
        
        # Konu etiketi ve girişi
        self.topic_label = ctk.CTkLabel(top_frame, text=_("topic"))
        self.topic_label.grid(row=0, column=0, padx=5, pady=10, sticky="w")
        
        topic_entry = ctk.CTkEntry(top_frame, textvariable=self.topic_var, width=400)
        topic_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        
        # Konu oluştur butonu
        self.topic_btn = ctk.CTkButton(top_frame, text=_("generate_topic"), command=self.generate_topic)
        self.topic_btn.grid(row=0, column=2, padx=5, pady=10)
        
        # Ana içerik - Log alanı
        content_frame = ctk.CTkFrame(self.home_frame)
        content_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # Log alanı
        self.log_label = ctk.CTkLabel(content_frame, text=_("log_title"))
        self.log_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.log_text = ctk.CTkTextbox(content_frame, height=300)
        self.log_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        # Ayarlar bölümü
        settings_frame = ctk.CTkFrame(self.home_frame)
        settings_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        settings_frame.grid_columnconfigure(1, weight=1)
        
        # Sürekli çalışma seçeneği
        self.continuous_check = ctk.CTkCheckBox(
            settings_frame, 
            text=_("continuous_mode"), 
            variable=self.continuous_var,
            command=self.toggle_continuous_mode
        )
        self.continuous_check.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Maksimum video sayısı
        self.max_videos_label = ctk.CTkLabel(settings_frame, text=_("max_videos"))
        self.max_videos_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        max_videos_entry = ctk.CTkEntry(settings_frame, textvariable=self.max_videos_var, width=50)
        max_videos_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Durum göstergesi
        self.status_label = ctk.CTkLabel(settings_frame, text=_("status"))
        self.status_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        status_value = ctk.CTkLabel(settings_frame, textvariable=self.status_var)
        status_value.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # Alt panel - Kontrol butonları
        button_frame = ctk.CTkFrame(self.home_frame)
        button_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        
        # Başlat butonu
        self.start_btn = ctk.CTkButton(button_frame, text=_("start"), command=self.start_process)
        self.start_btn.pack(side="left", padx=5, pady=5)
        
        # Durdur butonu
        self.stop_btn = ctk.CTkButton(button_frame, text=_("stop"), state="disabled", command=self.stop_process)
        self.stop_btn.pack(side="left", padx=5, pady=5)
        
        # YouTube ayarlarını kontrol et butonu
        self.yt_check_btn = ctk.CTkButton(button_frame, text=_("check_youtube"), command=self.check_youtube_settings)
        self.yt_check_btn.pack(side="right", padx=5, pady=5)

    def setup_api_frame(self):
        """API Keys sayfasını oluşturur"""
        # Ana düzen
        self.api_frame.grid_columnconfigure(0, weight=1)
        self.api_frame.grid_rowconfigure(5, weight=1)
        
        # Başlık
        self.api_title_label = ctk.CTkLabel(
            self.api_frame, 
            text=_("api_title"), 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.api_title_label.grid(row=0, column=0, padx=20, pady=(20, 30), sticky="w")
        
        # API Keys Ana Çerçeve
        api_keys_frame = ctk.CTkFrame(self.api_frame)
        api_keys_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        api_keys_frame.grid_columnconfigure(1, weight=1)
        
        # 1. OpenAI API Key
        self.openai_label = ctk.CTkLabel(api_keys_frame, text=_("openai_api"))
        self.openai_label.grid(row=0, column=0, padx=10, pady=15, sticky="w")
        
        openai_entry = ctk.CTkEntry(api_keys_frame, textvariable=self.openai_api_var, width=400, show="*")
        openai_entry.grid(row=0, column=1, padx=10, pady=15, sticky="ew")
        
        openai_help_btn = ctk.CTkButton(
            api_keys_frame, 
            text="?", 
            width=30, 
            command=lambda: self.show_api_help("openai")
        )
        openai_help_btn.grid(row=0, column=2, padx=10, pady=15)
        
        # 2. Pexels API Key
        self.pexels_label = ctk.CTkLabel(api_keys_frame, text=_("pexels_api"))
        self.pexels_label.grid(row=1, column=0, padx=10, pady=15, sticky="w")
        
        pexels_entry = ctk.CTkEntry(api_keys_frame, textvariable=self.pexels_api_var, width=400, show="*")
        pexels_entry.grid(row=1, column=1, padx=10, pady=15, sticky="ew")
        
        pexels_help_btn = ctk.CTkButton(
            api_keys_frame, 
            text="?", 
            width=30, 
            command=lambda: self.show_api_help("pexels")
        )
        pexels_help_btn.grid(row=1, column=2, padx=10, pady=15)
        
        # 3. YouTube API Key
        self.youtube_label = ctk.CTkLabel(api_keys_frame, text=_("youtube_api"))
        self.youtube_label.grid(row=2, column=0, padx=10, pady=15, sticky="w")
        
        youtube_entry = ctk.CTkEntry(api_keys_frame, textvariable=self.youtube_api_var, width=400, show="*")
        youtube_entry.grid(row=2, column=1, padx=10, pady=15, sticky="ew")
        
        youtube_help_btn = ctk.CTkButton(
            api_keys_frame, 
            text="?", 
            width=30, 
            command=lambda: self.show_api_help("youtube")
        )
        youtube_help_btn.grid(row=2, column=2, padx=10, pady=15)
        
        # 4. Pixabay API Key
        self.pixabay_label = ctk.CTkLabel(api_keys_frame, text=_("pixabay_api"))
        self.pixabay_label.grid(row=3, column=0, padx=10, pady=15, sticky="w")
        
        pixabay_entry = ctk.CTkEntry(api_keys_frame, textvariable=self.pixabay_api_var, width=400, show="*")
        pixabay_entry.grid(row=3, column=1, padx=10, pady=15, sticky="ew")
        
        pixabay_help_btn = ctk.CTkButton(
            api_keys_frame, 
            text="?", 
            width=30, 
            command=lambda: self.show_api_help("pixabay")
        )
        pixabay_help_btn.grid(row=3, column=2, padx=10, pady=15)
        
        # Göster/Gizle Checkbox
        self.show_keys_var = ctk.BooleanVar(value=False)
        self.show_keys_check = ctk.CTkCheckBox(
            self.api_frame, 
            text=_("show_keys"), 
            variable=self.show_keys_var,
            command=self.toggle_key_visibility
        )
        self.show_keys_check.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        
        # Kaydetme Butonu
        self.save_btn = ctk.CTkButton(
            self.api_frame, 
            text=_("save_settings"), 
            command=self.save_api_settings
        )
        self.save_btn.grid(row=3, column=0, padx=20, pady=20)
        
        # Durum Label'ı
        self.api_status_var = ctk.StringVar(value="")
        api_status_label = ctk.CTkLabel(
            self.api_frame, 
            textvariable=self.api_status_var,
            text_color="#4CAF50"
        )
        api_status_label.grid(row=4, column=0, padx=20, pady=5, sticky="w")
    
    def setup_settings_frame(self):
        """Ayarlar sayfasını oluşturur"""
        # Ana düzen
        self.settings_frame.grid_columnconfigure(0, weight=1)
        self.settings_frame.grid_rowconfigure(6, weight=1)
        
        # Başlık
        settings_title = ctk.CTkLabel(
            self.settings_frame, 
            text=_("settings"), 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        settings_title.grid(row=0, column=0, padx=20, pady=(20, 30), sticky="w")
        
        # Ayarlar ana çerçeve
        settings_content = ctk.CTkFrame(self.settings_frame)
        settings_content.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        settings_content.grid_columnconfigure(1, weight=1)
        
        # Arayüz dili ayarları
        ui_lang_label = ctk.CTkLabel(settings_content, text=_("ui_language"))
        ui_lang_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Arayüz dili dropdown
        ui_lang_options = get_language_options(_)
        ui_lang_values = [name for _, name in ui_lang_options]
        
        self.ui_lang_dropdown = ctk.CTkOptionMenu(
            settings_content,
            values=ui_lang_values,
            command=self.on_ui_language_select
        )
        self.ui_lang_dropdown.grid(row=0, column=1, padx=20, pady=15, sticky="w")
        
        # Başlangıç değerini ayarla
        current_ui_lang_code = self.ui_language_var.get()
        current_ui_lang_name = get_language_name(current_ui_lang_code, _)
        self.ui_lang_dropdown.set(current_ui_lang_name)
        
        # İçerik ve seslendirme dili ayarları (birleştirilmiş)
        content_lang_label = ctk.CTkLabel(settings_content, text=_("content_and_tts_language"))
        content_lang_label.grid(row=1, column=0, padx=20, pady=15, sticky="w")
        
        # İçerik dili dropdown
        content_lang_options = get_language_options(_)
        content_lang_values = [name for _, name in content_lang_options]
        
        self.content_lang_dropdown = ctk.CTkOptionMenu(
            settings_content,
            values=content_lang_values,
            command=self.on_content_language_select
        )
        self.content_lang_dropdown.grid(row=1, column=1, padx=20, pady=15, sticky="w")
        
        # Başlangıç değerini ayarla
        current_content_lang_code = self.content_language_var.get()
        current_content_lang_name = get_language_name(current_content_lang_code, _)
        self.content_lang_dropdown.set(current_content_lang_name)
        
        # Altyazı dili ayarları
        subtitle_lang_label = ctk.CTkLabel(settings_content, text=_("subtitle_language"))
        subtitle_lang_label.grid(row=2, column=0, padx=20, pady=15, sticky="w")
        
        # Altyazı dili dropdown
        subtitle_lang_options = get_language_options(_)
        subtitle_lang_values = [name for _, name in subtitle_lang_options]
        
        self.subtitle_lang_dropdown = ctk.CTkOptionMenu(
            settings_content,
            values=subtitle_lang_values,
            command=self.on_subtitle_language_select
        )
        self.subtitle_lang_dropdown.grid(row=2, column=1, padx=20, pady=15, sticky="w")
        
        # Başlangıç değerini ayarla
        current_subtitle_lang_code = self.subtitle_language_var.get()
        current_subtitle_lang_name = get_language_name(current_subtitle_lang_code, _)
        self.subtitle_lang_dropdown.set(current_subtitle_lang_name)
        
        # Dil ayarları açıklaması
        content_lang_info = ctk.CTkLabel(
            settings_content, 
            text=_("content_language_info"),
            wraplength=500,
            justify="left"
        )
        content_lang_info.grid(row=4, column=0, columnspan=2, padx=20, pady=(20, 20), sticky="w")
        
        # Ayarları kaydet butonu
        save_settings_btn = ctk.CTkButton(
            self.settings_frame,
            text=_("save_settings"),
            command=self.save_settings
        )
        save_settings_btn.grid(row=2, column=0, padx=20, pady=20, sticky="w")
        
        # Durum mesajı
        self.settings_status_var = ctk.StringVar(value="")
        settings_status = ctk.CTkLabel(
            self.settings_frame,
            textvariable=self.settings_status_var,
            text_color="#4CAF50"
        )
        settings_status.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")
    
    def on_ui_language_select(self, selected_name):
        """Arayüz dili seçimi değiştiğinde çağrılır"""
        # Seçilen dil adından dil kodunu bul
        for code, key in SUPPORTED_LANGUAGES.items():
            if _(key) == selected_name:
                self.ui_language_var.set(code)
                break
    
    def on_content_language_select(self, selected_name):
        """İçerik dili seçimi değiştiğinde çağrılır"""
        try:
            # Debug: Şu anki içerik dilini göster
            current_lang = self.content_language_var.get()
            self.add_log(f"Debug: Mevcut içerik dili: {current_lang}")
            
            # Debug: Seçilen dil adını göster
            self.add_log(f"Debug: Seçilen dil adı: {selected_name}")
            
            # Seçilen dil adından dil kodunu bul
            found = False
            for code, key in SUPPORTED_LANGUAGES.items():
                translated_name = _(key)
                # Debug: Kontrol edilen dili göster
                self.add_log(f"Debug: Kontrol: {code} -> {key} -> {translated_name}")
                
                if translated_name == selected_name:
                    # Yeni içerik dilini ayarla
                    self.content_language_var.set(code)
                    # Debug: Yeni içerik dilini göster
                    self.add_log(f"Debug: Yeni içerik dili ayarlandı: {code}")
                    
                    # Hemen config.json dosyasına da kaydet ki dil değişikliği kalıcı olsun
                    try:
                        config = self.load_config()
                        config["content_language"] = code
                        config["tts_language"] = code
                        with open("config.json", "w", encoding="utf-8") as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                        self.add_log(f"Debug: İçerik dili doğrudan config.json'a kaydedildi: {code}")
                    except Exception as save_error:
                        self.add_log(f"Debug: Config kaydetme hatası: {str(save_error)}")
                    
                    # Ekranda seçilen dili göster
                    self.add_log(f"{_('content_and_tts_language_changed')}: {selected_name}")
                    found = True
                    break
                    
            if not found:
                self.add_log(f"Debug: Dil kodu bulunamadı! Seçilen: {selected_name}")
                
        except Exception as e:
            self.add_log(f"{_('error_prefix')}{str(e)}")
    
    def on_subtitle_language_select(self, selected_name):
        """Altyazı dili seçimi değiştiğinde çağrılır"""
        try:
            # Debug: Şu anki altyazı dilini göster
            current_lang = self.subtitle_language_var.get()
            self.add_log(f"Debug: Mevcut altyazı dili: {current_lang}")
            
            # Debug: Seçilen dil adını göster
            self.add_log(f"Debug: Seçilen altyazı dili adı: {selected_name}")
            
            # Seçilen dil adından dil kodunu bul
            found = False
            for code, key in SUPPORTED_LANGUAGES.items():
                translated_name = _(key)
                # Debug: Kontrol edilen dili göster
                self.add_log(f"Debug: Altyazı kontrol: {code} -> {key} -> {translated_name}")
                
                if translated_name == selected_name:
                    # Yeni altyazı dilini ayarla
                    self.subtitle_language_var.set(code)
                    # Debug: Yeni altyazı dilini göster
                    self.add_log(f"Debug: Yeni altyazı dili ayarlandı: {code}")
                    
                    # Hemen config.json dosyasına da kaydet
                    try:
                        config = self.load_config()
                        config["subtitle_language"] = code
                        with open("config.json", "w", encoding="utf-8") as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                        self.add_log(f"Debug: Altyazı dili doğrudan config.json'a kaydedildi: {code}")
                    except Exception as save_error:
                        self.add_log(f"Debug: Altyazı dili config kaydetme hatası: {str(save_error)}")
                    
                    # Ekranda seçilen dili göster
                    self.add_log(f"{_('subtitle_language_changed')}: {selected_name}")
                    found = True
                    break
                    
            if not found:
                self.add_log(f"Debug: Altyazı dil kodu bulunamadı! Seçilen: {selected_name}")
                
        except Exception as e:
            self.add_log(f"{_('error_prefix')}{str(e)}")
    
    def on_language_change(self, *args):
        """Dil değiştiğinde UI'ı günceller"""
        lang = self.ui_language_var.get()
        
        # Dil yöneticisini güncelle
        language_manager.set_language(lang)
        
        # Pencere başlığını güncelle
        self.title(_("app_title"))
        
        # Durum mesajını güncelle (eğer hazır durumdaysa)
        if not self.is_running:
            self.status_var.set(_("ready"))
        
        # Menü öğelerini güncelle
        self.home_button.configure(text=_("home"))
        self.api_button.configure(text=_("api_keys"))
        self.settings_button.configure(text=_("settings"))
        self.appearance_mode_label.configure(text=_("appearance"))
        
        # Ana sayfa öğelerini güncelle
        self.topic_label.configure(text=_("topic"))
        self.topic_btn.configure(text=_("generate_topic"))
        self.log_label.configure(text=_("log_title"))
        self.continuous_check.configure(text=_("continuous_mode"))
        self.max_videos_label.configure(text=_("max_videos"))
        self.status_label.configure(text=_("status"))
        self.start_btn.configure(text=_("start"))
        self.stop_btn.configure(text=_("stop"))
        self.yt_check_btn.configure(text=_("check_youtube"))
        
        # API sayfası öğelerini güncelle
        self.api_title_label.configure(text=_("api_title"))
        self.openai_label.configure(text=_("openai_api"))
        self.pexels_label.configure(text=_("pexels_api"))
        self.youtube_label.configure(text=_("youtube_api"))
        self.pixabay_label.configure(text=_("pixabay_api"))
        self.show_keys_check.configure(text=_("show_keys"))
        self.save_btn.configure(text=_("save_settings"))
        
        # Dil dropdown'larını güncelle
        try:
            # Yeni dil listesini oluştur
            lang_options = get_language_options(_)
            lang_values = [name for _, name in lang_options]
            
            # Mevcut seçili değerleri al
            ui_lang_code = self.ui_language_var.get()
            content_lang_code = self.content_language_var.get()
            subtitle_lang_code = self.subtitle_language_var.get()
            
            # Dropdown'ları güncelle
            if hasattr(self, 'ui_lang_dropdown'):
                self.ui_lang_dropdown.configure(values=lang_values)
                self.ui_lang_dropdown.set(get_language_name(ui_lang_code, _))
                
            if hasattr(self, 'content_lang_dropdown'):
                self.content_lang_dropdown.configure(values=lang_values)
                self.content_lang_dropdown.set(get_language_name(content_lang_code, _))
                
            if hasattr(self, 'subtitle_lang_dropdown'):
                self.subtitle_lang_dropdown.configure(values=lang_values)
                self.subtitle_lang_dropdown.set(get_language_name(subtitle_lang_code, _))
        except Exception as e:
            print(f"Error updating language dropdowns: {str(e)}")
    
    def toggle_key_visibility(self):
        """API anahtarlarının görünürlüğünü değiştirir"""
        show_keys = self.show_keys_var.get()
        # API anahtarları girişlerini bul
        for widget in self.api_frame.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for entry in widget.winfo_children():
                    if isinstance(entry, ctk.CTkEntry):
                        entry.configure(show="" if show_keys else "*")
    
    def show_api_help(self, api_type):
        """API yardım popupını gösterir"""
        if api_type == "openai":
            HelpPopup(
                self,
                _("openai_help_title"),
                _("openai_help_content"),
                "https://platform.openai.com/api-keys",
                _("openai_help_link")
            )
        elif api_type == "pexels":
            HelpPopup(
                self,
                _("pexels_help_title"),
                _("pexels_help_content"),
                "https://www.pexels.com/api/",
                _("pexels_help_link")
            )
        elif api_type == "youtube":
            HelpPopup(
                self,
                _("youtube_help_title"),
                _("youtube_help_content"),
                "https://console.cloud.google.com/apis/dashboard",
                _("youtube_help_link")
            )
        elif api_type == "pixabay":
            HelpPopup(
                self,
                _("pixabay_help_title"),
                _("pixabay_help_content"),
                "https://pixabay.com/service/about/api/",
                _("pixabay_help_link")
            )
    
    def save_api_settings(self):
        """API anahtarlarını config.json dosyasına kaydeder"""
        try:
            # Mevcut config dosyasını yükle
            config = self.load_config()
            
            # API anahtarlarını güncelle
            config["openai_api_key"] = self.openai_api_var.get()
            config["pexels_api_key"] = self.pexels_api_var.get()
            config["youtube_api_key"] = self.youtube_api_var.get()
            config["pixabay_api_key"] = self.pixabay_api_var.get()
            config["language"] = self.language_var.get()
            
            # TTS dili ayarını güncelleyelim - içerik dili ile aynı olmalı
            content_lang = self.content_language_var.get()
            config["tts_language"] = content_lang
            
            # Config dosyasına kaydet
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Başarılı mesajını göster
            self.api_status_var.set(_("settings_saved"))
            self.after(3000, lambda: self.api_status_var.set(""))
            
        except Exception as e:
            # Hata mesajını göster
            self.api_status_var.set(f"{_('error_prefix')}{str(e)}")
            self.after(3000, lambda: self.api_status_var.set(""))

    def process_logs(self):
        """Log kuyruğundan mesajları işler"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.insert("end", f"[{self.get_time()}] {message}\n")
                self.log_text.see("end")  # Otomatik kaydır
                self.log_queue.task_done()
        except queue.Empty:
            pass
        
        # İşlemi tekrarla
        self.after(100, self.process_logs)
    
    def get_time(self):
        """Güncel zamanı formatlar"""
        return datetime.now().strftime("%H:%M:%S")

    def load_config(self):
        """API anahtarlarını ve ayarları config.json dosyasından yükler"""
        try:
            # Config dosyası var mı kontrol et
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    
                # API anahtarlarını yükle
                self.openai_api_var.set(config.get("openai_api_key", ""))
                self.pexels_api_var.set(config.get("pexels_api_key", ""))
                self.youtube_api_var.set(config.get("youtube_api_key", ""))
                self.pixabay_api_var.set(config.get("pixabay_api_key", ""))
                
                # Dil ayarlarını yükle
                ui_lang = config.get("ui_language", DEFAULT_UI_LANGUAGE)
                content_lang = config.get("content_language", DEFAULT_CONTENT_LANGUAGE)
                subtitle_lang = config.get("subtitle_language", DEFAULT_SUBTITLE_LANGUAGE)
                
                # Mevcut değerlerle config'deki değerler farklıysa gün
                # Eğer şu anki içerik dili config'den farklıysa ve boş değilse, 
                # config'i şu anki değere göre güncelle (dil seçimi yapıldıysa)
                current_content_lang = self.content_language_var.get()
                current_subtitle_lang = self.subtitle_language_var.get()
                config_changed = False
                
                # İçerik dili kontrolü
                if current_content_lang and current_content_lang != content_lang:
                    self.add_log(f"Debug: İçerik dili çakışması: UI'da {current_content_lang}, Config'de {content_lang}")
                    content_lang = current_content_lang
                    # Config'i güncelle
                    config["content_language"] = current_content_lang
                    config["tts_language"] = current_content_lang
                    config_changed = True
                    self.add_log(f"Debug: İçerik dili UI değerine göre güncellendi: {current_content_lang}")
                    
                # Altyazı dili kontrolü
                if current_subtitle_lang and current_subtitle_lang != subtitle_lang:
                    self.add_log(f"Debug: Altyazı dili çakışması: UI'da {current_subtitle_lang}, Config'de {subtitle_lang}")
                    subtitle_lang = current_subtitle_lang
                    # Config'i güncelle
                    config["subtitle_language"] = current_subtitle_lang
                    config_changed = True
                    self.add_log(f"Debug: Altyazı dili UI değerine göre güncellendi: {current_subtitle_lang}")
                
                # Eğer değişiklik varsa config dosyasını kaydet
                if config_changed:
                    with open("config.json", "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    self.add_log(f"Debug: Config dosyası UI değerlerine göre güncellendi")
                
                # Dilleri ayarla
                self.ui_language_var.set(ui_lang)
                self.content_language_var.set(content_lang)
                self.subtitle_language_var.set(subtitle_lang)
                
                # Yüklenen değerlerle ilgili debug mesajı
                self.add_log(f"Debug: Yüklenen dil ayarları: UI={ui_lang}, Content={content_lang}, Subtitle={subtitle_lang}")
                print(f"Yüklenen dil ayarları: UI={ui_lang}, Content={content_lang}, Subtitle={subtitle_lang}")
                
                # Arayüz dilini ayarla
                language_manager.set_language(self.ui_language_var.get())
                
                return config
            else:
                # Config dosyası yoksa oluştur
                config = {
                    "openai_api_key": "",
                    "pexels_api_key": "",
                    "youtube_api_key": "",
                    "pixabay_api_key": "",
                    "ui_language": DEFAULT_UI_LANGUAGE,
                    "content_language": DEFAULT_CONTENT_LANGUAGE,
                    "tts_language": DEFAULT_CONTENT_LANGUAGE,  # Artık content_language ile aynı
                    "subtitle_language": DEFAULT_SUBTITLE_LANGUAGE
                }
                with open("config.json", "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                return config
                
        except Exception as e:
            self.add_log(f"{_('error_prefix')}{str(e)}")
            return {}
            
    def save_settings(self):
        """Ayarları kaydeder"""
        try:
            # Config dosyasını yükle
            config = self.load_config()
            
            # İçerik dili
            content_lang = self.content_language_var.get()
            
            # Dil ayarlarını kaydet
            config["ui_language"] = self.ui_language_var.get()
            config["content_language"] = content_lang
            config["tts_language"] = content_lang  # İçerik dili ile aynı olmalı
            config["subtitle_language"] = self.subtitle_language_var.get()
            
            # Debug
            self.add_log(f"Debug: Kaydedilen içerik dili: {content_lang}")
            self.add_log(f"Debug: Kaydedilen tts dili: {content_lang}")
            
            # Dosyaya yaz
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
            # Başarı mesajı
            self.settings_status_var.set(_("settings_saved"))
            self.after(3000, lambda: self.settings_status_var.set(""))
            
        except Exception as e:
            self.settings_status_var.set(f"{_('error_prefix')}{str(e)}")
            self.after(3000, lambda: self.settings_status_var.set(""))

    def generate_topic(self):
        """Konu üreticisini çalıştırır"""
        try:
            # İçerik dilini al
            content_language = self.content_language_var.get()
            
            # OpenAI API key al
            openai_api_key = self.openai_api_var.get().strip()
            
            # API key kontrolü
            if not openai_api_key:
                self.add_log(_("error_no_openai_key"))
                return
            
            # Başlatma
            self.add_log(_("generate_topic"))
            
            def run_topic_gen():
                try:
                    # Dile göre uygun fonksiyonu çalıştır
                    if content_language == "en":
                        # İngilizce konu üretici
                        topic = generate_english_topic(openai_api_key)
                        self.add_log(f"Debug: İngilizce konu oluşturuldu")
                    elif content_language in ["es", "fr", "de", "it", "pt", "ru", "ar"]:
                        # Uluslararası diller için konu üretici
                        topic = generate_topic_international(openai_api_key, content_language)
                        self.add_log(f"Debug: {content_language} dilinde konu oluşturuldu")
                    else:
                        # Türkçe konu üretici (varsayılan)
                        topic = generate_topic(openai_api_key)
                        self.add_log(f"Debug: Türkçe konu oluşturuldu")
                    
                    # Oluşturulan konuyu UI'da güncelle
                    self.topic_var.set(topic)
                    self.add_log(f"{_('topic')}: {topic}")
                except Exception as e:
                    self.add_log(f"{_('error_prefix')}{str(e)}")
            
            # Yeni thread'de çalıştır
            threading.Thread(target=run_topic_gen).start()
            
        except Exception as e:
            self.add_log(f"{_('error_prefix')}{str(e)}")
    
    def start_process(self):
        """İşlemi başlatır"""
        try:
            # API anahtarlarını al
            openai_api_key = self.openai_api_var.get().strip()
            
            # OpenAI API key kontrolü
            if not openai_api_key:
                self.add_log(_("error_no_openai_key"))
                return
                
            # Konu kontrol et
            topic = self.topic_var.get().strip()
            if not topic:
                # Eğer sürekli mod etkinse ve konu boşsa, otomatik konu oluştur
                if self.continuous_var.get():
                    self.add_log(_("auto_generating_topic"))
                    content_language = self.content_language_var.get()
                    
                    # Güncel içerik dilini göster
                    self.add_log(f"Debug: Konu oluşturmada kullanılan dil: {content_language}")
                    
                    # İçerik diline göre konu oluştur
                    if content_language == "en":
                        topic = generate_english_topic(openai_api_key)
                        self.add_log(f"Debug: İngilizce konu otomatik oluşturuldu")
                    elif content_language in ["es", "fr", "de", "it", "pt", "ru", "ar"]:
                        # Uluslararası diller için konu üretici
                        topic = generate_topic_international(openai_api_key, content_language)
                        self.add_log(f"Debug: {content_language} dilinde konu otomatik oluşturuldu")
                    else:
                        topic = generate_topic(openai_api_key)
                        self.add_log(f"Debug: Türkçe konu otomatik oluşturuldu")
                        
                    self.topic_var.set(topic)
                    self.add_log(f"{_('topic')}: {topic}")
                else:
                    # Sürekli mod değilse ve konu boşsa, hata ver
                    self.add_log(_("error_no_topic"))
                    return
            
            # Zaten çalışıyor mu kontrol et
            if self.is_running:
                self.add_log(_("error_already_running"))
                return
                
            # Maksimum video sayısını al
            try:
                max_videos = int(self.max_videos_var.get())
                # 0 değeri sınırsız video üretimini ifade eder (None değeri olarak geçilecek)
                if max_videos == 0:
                    self.add_log("Sınırsız video üretim modu etkinleştirildi")
                    max_videos = None
                # Negatif değer girilmişse varsayılan olarak 1 yap
                elif max_videos < 0:
                    max_videos = 1
                    self.max_videos_var.set("1")
                    self.add_log("Geçersiz maksimum video sayısı. Değer 1 olarak ayarlandı.")
            except:
                # Hatalı giriş durumunda varsayılan olarak 5 yap
                max_videos = 5
                self.max_videos_var.set("5")
                self.add_log("Geçersiz maksimum video sayısı. Değer 5 olarak ayarlandı.")
                
            # Çalışma modunu al
            continuous = self.continuous_var.get()
            
            # Yeni bir işlem başlatılıyorsa video sayacını sıfırla
            if not hasattr(self, 'continuing_process') or not self.continuing_process:
                self.global_video_counter = 0
                self.add_log(f"Video sayacı sıfırlandı")
            else:
                # Devam eden bir işlem zinciri olduğunu belirt
                self.continuing_process = False
                
            # Son bir kez dosyadaki içerik dilini kontrol et, farklıysa güncelle
            try:
                # Config dosyasının güncel olduğundan emin olalım 
                content_language = self.content_language_var.get()
                subtitle_language = self.subtitle_language_var.get()
                self.add_log(f"Debug: Başlatmadan önce içerik dili: {content_language}")
                self.add_log(f"Debug: Başlatmadan önce altyazı dili: {subtitle_language}")
                
                if os.path.exists("config.json"):
                    with open("config.json", "r", encoding="utf-8") as f:
                        config = json.load(f)
                    
                    config_changed = False
                    
                    # İçerik ve TTS dili kontrolü
                    if config.get("content_language") != content_language or config.get("tts_language") != content_language:
                        self.add_log(f"Debug: Başlatmadan önce içerik/tts dili config.json güncelleniyor!")
                        config["content_language"] = content_language
                        config["tts_language"] = content_language
                        config_changed = True
                        
                    # Altyazı dili kontrolü
                    if config.get("subtitle_language") != subtitle_language:
                        self.add_log(f"Debug: Başlatmadan önce altyazı dili config.json güncelleniyor!")
                        config["subtitle_language"] = subtitle_language
                        config_changed = True
                    
                    # Eğer değişiklik varsa dosyayı güncelle
                    if config_changed:
                        with open("config.json", "w", encoding="utf-8") as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                        self.add_log("Debug: Config.json tam eşleşme için güncellendi")
            except Exception as e:
                self.add_log(f"Debug: Config son kontrol hatası: {str(e)}")
            
            # UI durumunu güncelle
            self.is_running = True
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.status_var.set(_("working"))
            
            # İşlem threadini başlat
            process_thread = threading.Thread(
                target=self.run_video_process,
                args=(topic, continuous, max_videos)
            )
            process_thread.daemon = True
            process_thread.start()
            
            # Sürekli mod için otomatik konu üretimi
            if continuous:
                def auto_generate_and_start():
                    try:
                        # Önceki işlem bitene kadar bekle
                        while self.is_running:
                            # Her 5 saniyede bir kontrol et
                            import time
                            time.sleep(5)
                        
                        # Eğer program hala çalışıyor ve sürekli mod aktifse
                        if not self.is_running and self.continuous_var.get():
                            # OpenAI API anahtarı kontrol et
                            if not openai_api_key:
                                self.add_log(_("error_no_openai_key"))
                                return
                                
                            # Bir sonraki işlem için boş konu ayarla - otomatik oluşturulacak
                            self.topic_var.set("")
                            self.add_log(_("preparing_next_video"))
                            
                            # Yeni işlemi başlat
                            self.after(2000, self.start_process)
                    except Exception as e:
                        self.add_log(f"{_('error_prefix')}{str(e)}")
                
                # Oto-yeniden başlatma işlemini ayrı bir thread'de başlat
                auto_thread = threading.Thread(target=auto_generate_and_start)
                auto_thread.daemon = True
                auto_thread.start()
                
        except Exception as e:
            self.is_running = False
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.status_var.set(_("error"))
            self.add_log(f"{_('error_prefix')}{str(e)}")
    
    def run_video_process(self, topic, continuous, max_videos):
        """Video oluşturma işlemini çalıştırır"""
        try:
            # Genel işlem durumu
            global_processing_state = {}
            
            # Üretilen video sayısını takip etmek için sayaç
            global_video_counter = getattr(self, 'global_video_counter', 0)
            
            # Log mesajları
            self.add_log(f"{_('process_started')}: {topic}")
            if continuous:
                self.add_log(_("continuous_mode_enabled"))
                # Maksimum video sayısı bilgisini göster
                if max_videos is not None:
                    self.add_log(f"Maksimum {max_videos} video üretilecek. Şu ana kadar üretilen: {global_video_counter}")
                else:
                    self.add_log(f"Sınırsız video üretim modu. Şu ana kadar üretilen: {global_video_counter}")
                
            # UI güncellemesi yapmak için kullanılacak fonksiyon
            def update_ui(message, is_error=False):
                self.add_log(message)
                if is_error:
                    self.status_var.set(_("error"))
            
            # Video limiti kontrolü - sürekli modda ve belirli bir limite ulaşıldıysa
            if continuous and max_videos is not None and global_video_counter >= max_videos:
                self.add_log(f"Maksimum video sayısına ({max_videos}) ulaşıldı. İşlem sonlandırılıyor.")
                self.process_completed()
                return
            
            # API anahtarlarını al
            openai_api_key = self.openai_api_var.get().strip()
            pexels_api_key = self.pexels_api_var.get().strip()
            youtube_api_key = self.youtube_api_var.get().strip()
            pixabay_api_key = self.pixabay_api_var.get().strip()
            
            # OpenAI API key kontrolü
            if not openai_api_key:
                update_ui(_("error_no_openai_key"), True)
                self.process_completed()
                return
                
            # Config.json dosyasından değil, doğrudan StringVar'dan dil bilgilerini al
            # Bu sayede UI'da seçilen dil doğrudan kullanılacak
            self.add_log(f"Debug: StringVar içerik dili değeri: {self.content_language_var.get()}")
            self.add_log(f"Debug: StringVar altyazı dili değeri: {self.subtitle_language_var.get()}")
            
            # İçerik ve altyazı dillerini al
            content_language = self.content_language_var.get()
            subtitle_language = self.subtitle_language_var.get()
            
            # Config.json dosyasındaki değerlerle kontrol et - eşleşmiyorsa güncelle
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                config_content_lang = config.get("content_language", "tr")
                config_tts_lang = config.get("tts_language", "tr")
                config_subtitle_lang = config.get("subtitle_language", "tr")
                
                # İçerik ve TTS dili kontrolü
                if config_content_lang != content_language or config_tts_lang != content_language:
                    self.add_log(f"Debug: Config.json ile içerik dili uyuşmazlığı tespit edildi!")
                    self.add_log(f"Debug: UI'da: {content_language}, Config'de: {config_content_lang}")
                    
                    # Config dosyasını güncelle
                    config["content_language"] = content_language
                    config["tts_language"] = content_language
                    
                    with open("config.json", "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    
                    self.add_log(f"Debug: Config.json güncellendi, içerik dili: {content_language}")
                
                # Altyazı dili kontrolü
                if config_subtitle_lang != subtitle_language:
                    self.add_log(f"Debug: Config.json ile altyazı dili uyuşmazlığı tespit edildi!")
                    self.add_log(f"Debug: UI'da: {subtitle_language}, Config'de: {config_subtitle_lang}")
                    
                    # Config dosyasını güncelle
                    config["subtitle_language"] = subtitle_language
                    
                    with open("config.json", "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    
                    self.add_log(f"Debug: Config.json güncellendi, altyazı dili: {subtitle_language}")
            except Exception as e:
                self.add_log(f"Debug: Config kontrol hatası: {str(e)}")
            
            # Debug: Seçilen dilleri göster
            self.add_log(f"Debug: İşlemdeki içerik dili: {content_language}")
            self.add_log(f"Debug: İşlemdeki altyazı dili: {subtitle_language}")
            
            # Dil uyumu kontrolü
            if not content_language:
                content_language = "tr"  # Varsayılan dil
                self.add_log(f"{_('warning_default_language')}: {content_language}")
                
            if not subtitle_language:
                subtitle_language = content_language
                self.add_log(f"{_('warning_subtitle_language_set')}: {subtitle_language}")
                
            # Gerekli işlem parametreleri
            params = {
                "topic": topic,
                "openai_api_key": openai_api_key,
                "pexels_api_key": pexels_api_key,
                "pixabay_api_key": pixabay_api_key,
                "youtube_api_key": youtube_api_key,
                "language": content_language,      # İçerik dili
                "tts_language": content_language,  # TTS dili içerik dili ile aynı
                "subtitle_language": subtitle_language,  # Altyazı dili
                "max_videos": max_videos,
                "continuous_mode": continuous,
                "log_callback": update_ui
            }
            
            # Debug: Parametre olarak geçilen dilleri göster
            self.add_log(f"Debug: Geçirilecek içerik dili: {params['language']}")
            self.add_log(f"Debug: Geçirilecek TTS dili: {params['tts_language']}")
            self.add_log(f"Debug: Geçirilecek altyazı dili: {params['subtitle_language']}")
            
            # Log için dil ayarlarını göster
            self.add_log(f"{_('using_content_and_tts_language')}: {content_language}")
            self.add_log(f"{_('using_subtitle_language')}: {subtitle_language}")
            
            # İşlemi başlat
            try:
                # İşlem başlamadan önce son bir kez dil ayarlarını kontrol et
                self.add_log(f"Debug: Son kontrol - İçerik dili: {params['language']}")
                self.add_log(f"Debug: Son kontrol - TTS dili: {params['tts_language']}")
                
                # Yeni bir asyncio loop oluştur
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # İşlemi başlat
                success, video_url = loop.run_until_complete(process_single_video(**params))
                
                # Loop'u temizle ve kapat
                loop.close()
                
                # İşlem sonucunu kaydet
                global_processing_state["success"] = success
                global_processing_state["video_url"] = video_url
                
                # Başarıyla tamamlandığını belirt
                if success:
                    # Video sayacını artır
                    global_video_counter += 1
                    self.global_video_counter = global_video_counter
                    self.add_log(f"Video başarıyla oluşturuldu ({global_video_counter}/{max_videos if max_videos is not None else 'Sınırsız'})")
                    self.add_log(_("process_completed"))
                else:
                    self.add_log(_("process_failed"), True)
                
            except Exception as e:
                # İşlem sırasında hata
                update_ui(f"{_('error_during_process')}: {str(e)}", True)
                global_processing_state["success"] = False
            
            # İşlem tamamlandı
            self.process_completed()
            
            # Sürekli mod aktif ise ve işlem başarılıysa, kısa bir beklemeden sonra yeni işlemi başlat
            if continuous and global_processing_state.get("success", False) and self.continuous_var.get():
                # Maksimum video sayısı kontrolü
                if max_videos is not None and global_video_counter >= max_videos:
                    self.add_log(f"Maksimum video sayısına ({max_videos}) ulaşıldı. İşlem sonlandırılıyor.")
                    # Sürekli çalışma modunu kapat
                    self.continuous_var.set(False)
                    self.add_log("Sürekli çalışma modu otomatik olarak kapatıldı")
                    return
                
                # Bir sonraki işlem için hazırlık mesajı
                self.add_log(_("preparing_next_video"))
                
                # Yeni işlem başlatmadan önce 10 saniye bekle
                time.sleep(10)
                
                # Yeni işlemi yalnızca durmuşsa başlat (paralel işlemleri önle)
                if not self.is_running:
                    # Devam eden bir süreç olduğunu belirt
                    self.continuing_process = True
                    # UI thread'inde yeni işlemi başlat
                    self.after(1000, self.start_process)
            
        except Exception as e:
            # Genel hata
            self.add_log(f"{_('error_prefix')}{str(e)}")
            self.process_completed()
    
    def process_completed(self):
        """İşlem tamamlandığında UI güncellemesi yapar"""
        # UI güncellemesini ana thread'de yap
        self.after(0, self.update_ui_after_completion)
    
    def update_ui_after_completion(self):
        """İşlem tamamlandıktan sonra UI güncellemesi yapar"""
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        if self.status_var.get() != _("error"):
            self.status_var.set(_("ready"))
    
    def stop_process(self):
        """Çalışan işlemi durdurur"""
        if self.is_running:
            self.is_running = False
            self.add_log(_("process_stopped"))
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.status_var.set(_("ready"))
    
    def toggle_continuous_mode(self):
        """Sürekli çalışma modunu açıp kapatır"""
        if self.continuous_var.get():
            self.add_log(_("continuous_mode_enabled"))
        else:
            self.add_log(_("continuous_mode_disabled"))
    
    def check_youtube_settings(self):
        """YouTube ayarlarını kontrol eder"""
        # YouTube API key kontrol et
        youtube_api_key = self.youtube_api_var.get().strip()
        
        if not youtube_api_key:
            self.add_log(_("error_no_youtube_key"))
            return
            
        # Client_secrets.json kontrol et
        client_secrets_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client_secrets.json")
        if not os.path.exists(client_secrets_file):
            self.add_log(_("error_no_client_secrets"))
            
            # Hata açıklaması
            help_message = _("youtube_setup_instructions")
            self.add_log(help_message)
            return
            
        # Kontroller başarılı
        self.add_log(_("youtube_settings_ok"))

    def add_log(self, message):
        """Log mesajı ekler"""
        self.log_queue.put(message)

def main():
    """Uygulamayı başlatır"""
    app = MMotoApp()
    app.mainloop()

if __name__ == "__main__":
    main() 