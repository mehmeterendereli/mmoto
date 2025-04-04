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

# Ana programdan içe aktarmalar
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import process_single_video
from modules.topic_generator import generate_topic, generate_english_topic

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
            text="Kapat", 
            command=self.destroy
        )
        close_button.pack(side="right", padx=10)

class MMotoApp(ctk.CTk):
    """Ana uygulama sınıfı"""
    def __init__(self):
        super().__init__()
        
        # Ana pencere ayarları
        self.title("MMoto Video Oluşturucu")
        self.geometry("1000x700")
        self.minsize(800, 600)
        
        # Tema ayarı
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Değişkenler
        self.topic_var = ctk.StringVar()
        self.status_var = ctk.StringVar(value="Hazır")
        self.continuous_var = ctk.BooleanVar(value=False)
        self.max_videos_var = ctk.StringVar(value="5")
        self.language_var = ctk.StringVar(value="tr")
        self.is_running = False
        self.current_page = "home"
        
        # API anahtarları değişkenleri
        self.openai_api_var = ctk.StringVar()
        self.pexels_api_var = ctk.StringVar()
        self.youtube_api_var = ctk.StringVar()
        self.pixabay_api_var = ctk.StringVar()
        
        # Log kuyruğu
        self.log_queue = queue.Queue()
        
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
        
        # Ayarları yükle
        self.load_config()
        
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
            text="Ana Sayfa",
            command=self.show_home_page
        )
        self.home_button.grid(row=1, column=0, padx=20, pady=10)
        
        self.api_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="API Anahtarları",
            command=self.show_api_page
        )
        self.api_button.grid(row=2, column=0, padx=20, pady=10)
        
        # Görünüm seçici (light/dark mode)
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Görünüm:", anchor="w")
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
        
        # Home Frame (Ana Sayfa)
        self.setup_home_frame()
        
        # API Keys Frame
        self.setup_api_frame()
    
    def change_appearance_mode(self, new_appearance_mode):
        """Görünüm modunu değiştirir"""
        ctk.set_appearance_mode(new_appearance_mode)
        
    def show_home_page(self):
        """Ana sayfayı gösterir"""
        self.current_page = "home"
        self.home_frame.pack(fill="both", expand=True)
        self.api_frame.pack_forget()
        self.home_button.configure(fg_color=APP_COLOR_PRIMARY)
        self.api_button.configure(fg_color="transparent")
        
    def show_api_page(self):
        """API Keys sayfasını gösterir"""
        self.current_page = "api"
        self.api_frame.pack(fill="both", expand=True)
        self.home_frame.pack_forget()
        self.api_button.configure(fg_color=APP_COLOR_PRIMARY)
        self.home_button.configure(fg_color="transparent")
        
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
        ctk.CTkLabel(top_frame, text="Konu:").grid(row=0, column=0, padx=5, pady=10, sticky="w")
        topic_entry = ctk.CTkEntry(top_frame, textvariable=self.topic_var, width=400)
        topic_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        
        # Konu oluştur butonu
        topic_btn = ctk.CTkButton(top_frame, text="Konu Oluştur", command=self.generate_topic)
        topic_btn.grid(row=0, column=2, padx=5, pady=10)
        
        # Ana içerik - Log alanı
        content_frame = ctk.CTkFrame(self.home_frame)
        content_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # Log alanı
        log_label = ctk.CTkLabel(content_frame, text="İşlem Günlüğü:")
        log_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.log_text = ctk.CTkTextbox(content_frame, height=300)
        self.log_text.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        # Ayarlar bölümü
        settings_frame = ctk.CTkFrame(self.home_frame)
        settings_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        settings_frame.grid_columnconfigure(1, weight=1)
        
        # Sürekli çalışma seçeneği
        continuous_check = ctk.CTkCheckBox(
            settings_frame, 
            text="Sürekli Çalışma Modu", 
            variable=self.continuous_var,
            command=self.toggle_continuous_mode
        )
        continuous_check.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Dil seçimi
        lang_label = ctk.CTkLabel(settings_frame, text="Dil:")
        lang_label.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        
        # Radiobutton'lar için frame
        lang_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        lang_frame.grid(row=0, column=2, padx=5, pady=5, sticky="e")
        
        tr_radio = ctk.CTkRadioButton(lang_frame, text="Türkçe", variable=self.language_var, value="tr")
        tr_radio.pack(side="left", padx=5)
        
        en_radio = ctk.CTkRadioButton(lang_frame, text="İngilizce", variable=self.language_var, value="en")
        en_radio.pack(side="left", padx=5)
        
        # Maksimum video sayısı
        max_videos_label = ctk.CTkLabel(settings_frame, text="Maksimum Video Sayısı:")
        max_videos_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        max_videos_entry = ctk.CTkEntry(settings_frame, textvariable=self.max_videos_var, width=50)
        max_videos_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Durum göstergesi
        status_label = ctk.CTkLabel(settings_frame, text="Durum:")
        status_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        status_value = ctk.CTkLabel(settings_frame, textvariable=self.status_var)
        status_value.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # Alt panel - Kontrol butonları
        button_frame = ctk.CTkFrame(self.home_frame)
        button_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        
        # Başlat butonu
        self.start_btn = ctk.CTkButton(button_frame, text="Başlat", command=self.start_process)
        self.start_btn.pack(side="left", padx=5, pady=5)
        
        # Durdur butonu
        self.stop_btn = ctk.CTkButton(button_frame, text="Durdur", state="disabled", command=self.stop_process)
        self.stop_btn.pack(side="left", padx=5, pady=5)
        
        # YouTube ayarlarını kontrol et butonu
        yt_check_btn = ctk.CTkButton(button_frame, text="YouTube Ayarlarını Kontrol Et", command=self.check_youtube_settings)
        yt_check_btn.pack(side="right", padx=5, pady=5)

    def setup_api_frame(self):
        """API Keys sayfasını oluşturur"""
        # Ana düzen
        self.api_frame.grid_columnconfigure(0, weight=1)
        self.api_frame.grid_rowconfigure(5, weight=1)
        
        # Başlık
        title_label = ctk.CTkLabel(
            self.api_frame, 
            text="API Anahtarları", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=(20, 30), sticky="w")
        
        # API Keys Ana Çerçeve
        api_keys_frame = ctk.CTkFrame(self.api_frame)
        api_keys_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        api_keys_frame.grid_columnconfigure(1, weight=1)
        
        # 1. OpenAI API Key
        openai_label = ctk.CTkLabel(api_keys_frame, text="OpenAI API Key:")
        openai_label.grid(row=0, column=0, padx=10, pady=15, sticky="w")
        
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
        pexels_label = ctk.CTkLabel(api_keys_frame, text="Pexels API Key:")
        pexels_label.grid(row=1, column=0, padx=10, pady=15, sticky="w")
        
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
        youtube_label = ctk.CTkLabel(api_keys_frame, text="YouTube API Key:")
        youtube_label.grid(row=2, column=0, padx=10, pady=15, sticky="w")
        
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
        pixabay_label = ctk.CTkLabel(api_keys_frame, text="Pixabay API Key:")
        pixabay_label.grid(row=3, column=0, padx=10, pady=15, sticky="w")
        
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
        show_keys_check = ctk.CTkCheckBox(
            self.api_frame, 
            text="API Anahtarlarını Göster", 
            variable=self.show_keys_var,
            command=self.toggle_key_visibility
        )
        show_keys_check.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        
        # Kaydetme Butonu
        save_btn = ctk.CTkButton(
            self.api_frame, 
            text="Ayarları Kaydet", 
            command=self.save_api_settings
        )
        save_btn.grid(row=3, column=0, padx=20, pady=20)
        
        # Durum Label'ı
        self.api_status_var = ctk.StringVar(value="")
        api_status_label = ctk.CTkLabel(
            self.api_frame, 
            textvariable=self.api_status_var,
            text_color="#4CAF50"
        )
        api_status_label.grid(row=4, column=0, padx=20, pady=5, sticky="w")
        
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
                "OpenAI API Key Nasıl Alınır",
                "OpenAI API Key almak için şu adımları izleyin:\n\n"
                "1. OpenAI hesabınıza giriş yapın (yoksa kaydolun)\n"
                "2. Sağ üst köşedeki profil menüsüne tıklayın\n"
                "3. 'View API Keys' seçeneğini seçin\n"
                "4. 'Create new secret key' butonuna tıklayın\n"
                "5. Oluşturulan anahtarı kopyalayın ve bu alana yapıştırın\n\n"
                "NOT: API anahtarınız 'sk-...' ile başlar ve yaklaşık 50 karakter uzunluğundadır.",
                "https://platform.openai.com/api-keys",
                "OpenAI API Keys Sayfasına Git"
            )
        elif api_type == "pexels":
            HelpPopup(
                self,
                "Pexels API Key Nasıl Alınır",
                "Pexels API Key almak için şu adımları izleyin:\n\n"
                "1. Pexels hesabınıza giriş yapın (yoksa kaydolun)\n"
                "2. https://www.pexels.com/api/new/ adresine gidin\n"
                "3. 'Your API Key' bölümünden anahtarınızı kopyalayın\n"
                "4. Kopyaladığınız anahtarı bu alana yapıştırın\n\n"
                "NOT: Pexels API anahtarı yaklaşık 30-40 karakter uzunluğundadır.",
                "https://www.pexels.com/api/",
                "Pexels API Sayfasına Git"
            )
        elif api_type == "youtube":
            HelpPopup(
                self,
                "YouTube API Key Nasıl Alınır",
                "YouTube API Key almak için şu adımları izleyin:\n\n"
                "1. Google Cloud Console'a giriş yapın\n"
                "2. Bir proje oluşturun (yoksa)\n"
                "3. API Kütüphanesi'nden YouTube Data API v3'ü etkinleştirin\n"
                "4. Kimlik Bilgileri menüsünden API anahtarı oluşturun\n"
                "5. Oluşturulan anahtarı bu alana yapıştırın\n\n"
                "NOT: YouTube API anahtarı 'AIzaSy...' ile başlar.",
                "https://console.cloud.google.com/apis/dashboard",
                "Google Cloud Console'a Git"
            )
        elif api_type == "pixabay":
            HelpPopup(
                self,
                "Pixabay API Key Nasıl Alınır",
                "Pixabay API Key almak için şu adımları izleyin:\n\n"
                "1. Pixabay hesabınıza giriş yapın (yoksa kaydolun)\n"
                "2. https://pixabay.com/api/docs/ adresine gidin\n"
                "3. Sayfanın alt tarafındaki 'API Key Request' bölümünü doldurun\n"
                "4. Onay e-postasıyla aldığınız API anahtarını bu alana yapıştırın\n\n"
                "NOT: Pixabay API anahtarı 15-20 karakter uzunluğunda rakam ve harflerden oluşur.",
                "https://pixabay.com/service/about/api/",
                "Pixabay API Sayfasına Git"
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
            
            # Config dosyasına kaydet
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Başarılı mesajını göster
            self.api_status_var.set("API anahtarları başarıyla kaydedildi!")
            self.after(3000, lambda: self.api_status_var.set(""))
            
        except Exception as e:
            # Hata mesajını göster
            self.api_status_var.set(f"Hata: {str(e)}")
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
        """Konfigürasyon dosyasını yükler ve değişkenleri doldurur"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                
                # API anahtarlarını değişkenlere ata
                self.openai_api_var.set(config.get("openai_api_key", ""))
                self.pexels_api_var.set(config.get("pexels_api_key", ""))
                self.youtube_api_var.set(config.get("youtube_api_key", ""))
                self.pixabay_api_var.set(config.get("pixabay_api_key", ""))
                
                return config
        except Exception as e:
            self.add_log(f"Konfigürasyon yükleme hatası: {str(e)}")
            return {}
    
    def generate_topic(self):
        """OpenAI API ile otomatik konu üretme"""
        try:
            self.add_log("Konu oluşturuluyor...")
            config = self.load_config()
            
            # API anahtarını kontrol et
            api_key = config.get("openai_api_key", "")
            if not api_key:
                self.add_log("Hata: OpenAI API anahtarı bulunamadı!")
                return
            
            # Yeni thread'de konu üret (arayüzü bloke etmemek için)
            def run_topic_gen():
                try:
                    # Dil seçimine göre uygun fonksiyonu çağır
                    if self.language_var.get() == "en":
                        topic = generate_english_topic(api_key)
                    else:
                        topic = generate_topic(api_key)
                    
                    self.topic_var.set(topic)
                    self.add_log(f"Konu oluşturuldu: {topic}")
                except Exception as e:
                    self.add_log(f"Konu oluşturma hatası: {str(e)}")
            
            threading.Thread(target=run_topic_gen).start()
            
        except Exception as e:
            self.add_log(f"Hata: {str(e)}")
    
    def start_process(self):
        """Video oluşturma işlemini başlatır"""
        # Sürekli mod ayarları
        continuous = self.continuous_var.get()
        max_videos = None
        
        if continuous:
            try:
                max_videos = int(self.max_videos_var.get())
                if max_videos <= 0:
                    max_videos = 1
                    self.max_videos_var.set("1")
            except:
                max_videos = 5
                self.max_videos_var.set("5")
        
        # Konu kontrolü
        topic = self.topic_var.get().strip()
        
        # Sürekli çalışma modunda ve konu boşsa, otomatik konu oluştur
        if continuous and not topic:
            self.add_log("Sürekli çalışma modu: Otomatik konu oluşturuluyor...")
            
            # Buton durumlarını güncelle (hemen devre dışı bırakalım)
            self.is_running = True
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.status_var.set("Çalışıyor...")
            
            # Konu oluşturma işlemi için yeni thread başlat
            def auto_generate_and_start():
                config = self.load_config()
                api_key = config.get("openai_api_key", "")
                
                if not api_key:
                    self.add_log("Hata: OpenAI API anahtarı bulunamadı!")
                    self.process_completed()
                    return
                
                try:
                    # Dil seçimine göre uygun fonksiyonu çağır
                    if self.language_var.get() == "en":
                        auto_topic = generate_english_topic(api_key)
                    else:
                        auto_topic = generate_topic(api_key)
                    
                    self.topic_var.set(auto_topic)
                    self.add_log(f"Otomatik konu oluşturuldu: {auto_topic}")
                    
                    # Şimdi video işlemini başlat
                    process_thread = threading.Thread(
                        target=self.run_video_process,
                        args=(auto_topic, continuous, max_videos)
                    )
                    process_thread.daemon = True
                    process_thread.start()
                    
                except Exception as e:
                    self.add_log(f"Otomatik konu oluşturma hatası: {str(e)}")
                    self.process_completed()
            
            threading.Thread(target=auto_generate_and_start).start()
            return
            
        # Normal durum - konu manuel girilmiş
        if not topic:
            self.add_log("Lütfen bir konu girin veya oluşturun!")
            return
        
        # Buton durumlarını güncelle
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_var.set("Çalışıyor...")
        
        # Ayrı bir thread'de işlemi başlat
        process_thread = threading.Thread(
            target=self.run_video_process,
            args=(topic, continuous, max_videos)
        )
        process_thread.daemon = True
        process_thread.start()
    
    def run_video_process(self, topic, continuous, max_videos):
        """Video işleme işlemini yürüten fonksiyon"""
        # Tek video işlemi için
        if not continuous:
            self.add_log(f"'{topic}' konusu için video oluşturma başlatılıyor...")
            
            # Asenkron işlem için event loop oluştur
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Video işleme fonksiyonunu çağır
                success, video_url = loop.run_until_complete(process_single_video(topic))
                
                if success:
                    self.add_log("Video başarıyla oluşturuldu!")
                    if video_url:
                        self.add_log(f"Video URL: {video_url}")
                else:
                    self.add_log("Video oluşturma başarısız oldu.")
            except Exception as e:
                self.add_log(f"Hata: {str(e)}")
            finally:
                loop.close()
                self.process_completed()
                
        # Sürekli çalışma modu
        else:
            self.add_log("Sürekli çalışma modu başlatılıyor...")
            self.add_log(f"Maksimum video sayısı: {max_videos}")
            
            # Asenkron işlem için event loop oluştur
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # İşlem sayacı
            video_count = 0
            config = self.load_config()
            
            try:
                while self.is_running and (max_videos is None or video_count < max_videos):
                    if video_count > 0:
                        # İlk turda kullanıcının girdiği konuyu kullan
                        # Sonraki turlarda otomatik konu üret
                        self.add_log("Yeni konu oluşturuluyor...")
                        if self.language_var.get() == "en":
                            topic = generate_english_topic(config.get("openai_api_key", ""))
                        else:
                            topic = generate_topic(config.get("openai_api_key", ""))
                        self.topic_var.set(topic)
                        self.add_log(f"Yeni konu: {topic}")
                    
                    self.add_log(f"Video {video_count+1}/{max_videos} oluşturuluyor: '{topic}'")
                    
                    # Video oluştur
                    success, video_url = loop.run_until_complete(process_single_video(topic))
                    
                    if success:
                        video_count += 1
                        self.add_log(f"Video {video_count}/{max_videos} başarıyla oluşturuldu!")
                        if video_url:
                            self.add_log(f"Video URL: {video_url}")
                    else:
                        self.add_log("Video oluşturma başarısız oldu.")
                    
                    # Hala çalışıyor mu kontrol et
                    if not self.is_running:
                        self.add_log("İşlem kullanıcı tarafından durduruldu.")
                        break
                    
                    # Maksimum sayıya ulaşıldı mı?
                    if max_videos is not None and video_count >= max_videos:
                        self.add_log(f"Maksimum video sayısına ({max_videos}) ulaşıldı.")
                        break
                    
                    # API limitlerini aşmamak için bekle
                    if self.is_running and video_count < max_videos:
                        self.add_log("Sonraki video için 20 saniye bekleniyor...")
                        for i in range(20):
                            if not self.is_running:
                                break
                            loop.run_until_complete(asyncio.sleep(1))
            
            except Exception as e:
                self.add_log(f"Hata: {str(e)}")
            finally:
                loop.close()
                self.process_completed()
    
    def process_completed(self):
        """İşlem tamamlandığında çağrılır"""
        # Ana thread üzerinde UI güncellemesi yap
        self.after(0, lambda: self.update_ui_after_completion())
    
    def update_ui_after_completion(self):
        """İşlem tamamlandıktan sonra UI güncellemesi"""
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_var.set("Tamamlandı")
        self.add_log("İşlem tamamlandı.")
    
    def stop_process(self):
        """Çalışan işlemi durdurur"""
        self.is_running = False
        self.add_log("İşlem durduruluyor... (Lütfen bekleyin)")
        self.status_var.set("Durduruluyor...")
        # Butonları devre dışı bırak
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="disabled")
    
    def toggle_continuous_mode(self):
        """Sürekli çalışma modu değiştiğinde çağrılır"""
        if self.continuous_var.get():
            self.add_log("Sürekli çalışma modu etkinleştirildi")
        else:
            self.add_log("Sürekli çalışma modu devre dışı bırakıldı")
    
    def check_youtube_settings(self):
        """YouTube ayarlarını kontrol eder"""
        # MMotoYT klasörünü kontrol et
        mmoto_yt_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MMotoYT")
        
        if not os.path.exists(mmoto_yt_dir):
            self.add_log(f"Hata: MMotoYT dizini bulunamadı: {mmoto_yt_dir}")
            return
        
        # Token dosyasını kontrol et
        tokens_path = os.path.join(mmoto_yt_dir, "tokens.json")
        if os.path.exists(tokens_path):
            self.add_log("YouTube kimlik doğrulaması mevcut.")
        else:
            self.add_log("YouTube kimlik doğrulaması bulunamadı. İlk video yüklemesinden önce yetkilendirme gerekecek.")
        
        # Client secret dosyasını kontrol et
        client_secret_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client_secret.json")
        if os.path.exists(client_secret_path):
            self.add_log("YouTube client_secret.json dosyası mevcut.")
        else:
            self.add_log("Uyarı: client_secret.json dosyası bulunamadı! YouTube yükleme çalışmayacak.")
    
    def add_log(self, message):
        """Log mesajını kuyruğa ekler"""
        self.log_queue.put(message)

def main():
    app = MMotoApp()
    app.mainloop()

if __name__ == "__main__":
    main() 