# MMoto - Otomatik Video İçerik Oluşturucu

MMoto, metin tabanlı girdileri kullanarak otomatik video içeriği oluşturan çok dilli bir Python uygulamasıdır. OpenAI API, Pexels API, Pixabay API gibi çeşitli API'ler kullanarak, belirlenen konular hakkında içerik oluşturur, ilgili görselleri bulur ve profesyonel kalitede videolar üretir.

## Özellikler

- **Çok Dilli Destek**: Türkçe, İngilizce, İspanyolca, Fransızca ve Almanca içerik üretimi
- **Gelişmiş İçerik Üretimi**: OpenAI API kullanarak farklı dillerde kaliteli içerik üretimi
- **Akıllı Anahtar Kelime Çıkarıcı**: İçerikten otomatik anahtar kelime çıkarımı 
- **Çoklu Video Kaynağı**: Pexels ve Pixabay API ile uygun video bulma
- **Profesyonel Ses Desteği**: OpenAI TTS ile farklı dillerde doğal ses oluşturma
- **Akıllı Altyazı Sistemi**: Otomatik çeviri ile farklı dillerde altyazı ekleyebilme
- **Otomatik Video İşleme**: Videolar arasında geçiş efektleri ve görsel iyileştirmeler
- **YouTube Entegrasyonu**: Tek tıkla YouTube'a video yükleme desteği
- **Kullanıcı Dostu Arayüz**: CustomTkinter ile modern bir kullanıcı arayüzü
- **Sürekli Üretim Modu**: Arka arkaya otomatik video üretimi yapabilme
- **İstatistik Takibi**: Üretilen videoların istatistiklerini kaydetme ve takip etme

## Kurulum

1. Depoyu klonlayın:
```bash
git clone https://github.com/mehmeterendereli/mmoto.git
cd MMoto
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. Gerekli API anahtarlarını ayarlayın:
   - `config.example.json` dosyasını `config.json` olarak kopyalayın
   - Aşağıdaki API anahtarlarını `config.json` dosyasına ekleyin:
     - OpenAI API anahtarı
     - Pexels API anahtarı
     - Pixabay API anahtarı (opsiyonel)
     - YouTube API anahtarı (YouTube yüklemeleri için)

## Kullanım

### Grafiksel Arayüz ile Kullanım:

```bash
python mmoto_gui.py
```

### Komut Satırı ile Kullanım:

```bash
python main.py [konu] --language tr --tts_language tr --subtitle_language tr
```

veya sürekli mod ile:

```bash
python main.py --continuous --max_videos 5 --language en
```

## Dil Desteği

MMoto şu dilleri destekler:
- Türkçe (tr)
- İngilizce (en)
- İspanyolca (es)
- Fransızca (fr)
- Almanca (de)

Her bileşen için farklı dil ayarları yapılabilir:
- İçerik dili: Videonun ana içeriğinin oluşturulacağı dil
- TTS dili: Seslendirme için kullanılacak dil
- Altyazı dili: Altyazıların görüntüleneceği dil

## Sistem Gereksinimleri

- Python 3.8 veya üstü
- FFmpeg 4.0 veya üstü (video işleme için)
- İnternet bağlantısı (API istekleri için)
- Minimum 4GB RAM

## Dosya Yapısı

- `main.py`: Ana program ve komut satırı arayüzü
- `mmoto_gui.py`: Grafiksel kullanıcı arayüzü
- `modules/`: Fonksiyonel modüller
  - `content_generator.py`: İçerik oluşturma
  - `keyword_extractor.py`: Anahtar kelime çıkarıcı
  - `topic_generator.py`: Konu oluşturucu
  - `video_fetcher.py`: Video bulma ve indirme
  - `video_processor.py`: Video işleme
  - `tts_generator.py`: Ses oluşturma
  - `subtitle_renderer.py`: Altyazı oluşturma ve ekleme
  - `audio_merger.py`: Ses ve video birleştirme
  - `closing_scene_adder.py`: Kapanış sahnesi ekleme
  - `youtube_uploader.py`: YouTube'a video yükleme
  - `metadata_writer.py`: Meta veri ve açıklama oluşturma
- `langs/`: Dil dosyaları
  - `tr.py`: Türkçe dil paketi
  - `en.py`: İngilizce dil paketi
- `utils/`: Yardımcı fonksiyonlar
- `assets/`: Statik dosyalar (logolar, şablonlar, vb.)
- `output/`: Oluşturulan içerikler
- `stats/`: İstatistik kayıtları

## Lisans

Bu proje MIT Lisansı altında dağıtılmaktadır.

## Katkıda Bulunma

Projeye katkıda bulunmak isteyenler için GitHub üzerinden pull request'ler açıktır. Hata raporları ve öneriler için issues bölümünü kullanabilirsiniz.
