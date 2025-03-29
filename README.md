# MMoto - Merak Makinesi

MMoto (Merak Makinesi), yapay zeka kullanarak bilgilendirici kısa videolar üreten bir video içerik üretme aracıdır. Bu araç, verilen bir konu hakkında OpenAI API kullanarak metin içeriği üretir, bu metni seslendirme için TTS (Text-to-Speech) teknolojisini kullanır ve ardından üretilen sesi ve altyazıları uygun videolar ile birleştirir.

## Özellikler

- OpenAI API ile yapay zeka destekli metin içeriği üretimi
- OpenAI TTS API ile profesyonel kalitede seslendirme
- Pexels API ile otomatik video indirme ve 9:16 formatına dönüştürme
- Kelime bazlı altyazı ekleme ve video-ses senkronizasyonu
- Kapanış videosu ekleme ve final video oluşturma
- Anahtar kelime öncelikli video seçim algoritması

## Gereksinimler

- Python 3.x
- FFmpeg - Video işleme için gerekli
- OpenAI API anahtarı (GPT-4o ve TTS API'leri için)
- Pexels API anahtarı (Video indirme için)
- İnternet bağlantısı

## Kurulum

1. Repoyu klonlayın:
```
git clone https://github.com/mehmeterendereli/mmoto.git
cd mmoto
```

2. Gerekli Python paketlerini yükleyin:
```
pip install -r requirements.txt
```

3. FFmpeg'i indirin ve kurun:
   - [FFmpeg'in resmi sitesinden](https://ffmpeg.org/download.html) FFmpeg'i indirin
   - İndirdiğiniz dosyaları `bin/bin/` klasörüne yerleştirin:
     - `ffmpeg.exe`
     - `ffprobe.exe`
     - `ffplay.exe`
   - Alternatif olarak, FFmpeg'i sistem yolunuza ekleyebilir ve `config.json` dosyasındaki yolları güncelleyebilirsiniz.

4. `config.example.json` dosyasını `config.json` olarak kopyalayın ve API anahtarlarınızı ekleyin:
```json
{
  "openai_api_key": "YOUR_OPENAI_API_KEY",
  "pexels_api_key": "YOUR_PEXELS_API_KEY",
  "youtube_api_key": "YOUR_YOUTUBE_API_KEY",
  "default_tts_voice": "onyx",
  "font_path": "assets/fonts/Montserrat-Bold.ttf",
  "video_resolution": [1080, 1920],
  "closing_video_path": "assets/kapanis.mp4",
  "ffmpeg_path": "bin/bin/ffmpeg.exe",
  "ffprobe_path": "bin/bin/ffprobe.exe"
}
```

## Kullanım

Temel kullanım için şu komutu çalıştırın:
```
python main.py
```

Program sizden bir konu girmenizi isteyecektir. Konu girdikten sonra, program şu adımları otomatik olarak gerçekleştirecektir:

1. Konu hakkında içerik üretme
2. İçerikten anahtar kelimeler çıkarma
3. Anahtar kelimelere göre video indirme
4. Videoları işleme ve birleştirme
5. Metni sese dönüştürme
6. Altyazı ekleme
7. Ses ve videoyu birleştirme
8. Kapanış sahnesi ekleme
9. Final videoyu oluşturma

## Dizin Yapısı

- `main.py` - Ana program
- `modules/` - İşlevsellik modüllerini içerir
  - `content_generator.py` - OpenAI API ile içerik üretir
  - `keyword_extractor.py` - İçerikten anahtar kelimeler çıkarır
  - `video_fetcher.py` - Pexels API ile videolar indirir
  - `video_processor.py` - Videoları işler ve birleştirir
  - `tts_generator.py` - Metni sese dönüştürür
  - `subtitle_renderer.py` - Altyazı ekler
  - `audio_merger.py` - Ses dosyalarını videoyla birleştirir
  - `closing_scene_adder.py` - Kapanış sahnesini ekler
  - `metadata_writer.py` - Video meta verilerini kaydeder
  - `project_initializer.py` - Proje klasörünü oluşturur
- `assets/` - Font, kapanış videosu vb. dosyaları içerir
- `output/` - Üretilen videoların kaydedildiği klasör
- `bin/` - FFmpeg gibi harici araçlar için klasör
- `utils/` - Yardımcı araçlar ve ek özellikler

## Özelleştirme

- `config.json`'da farklı bir ses tercih etmek için `default_tts_voice` değerini değiştirebilirsiniz (örn. "alloy", "echo", "fable", "onyx", "nova", "shimmer").
- Video çözünürlüğünü `config.json` dosyasındaki `video_resolution` değerini değiştirerek özelleştirebilirsiniz.
- Kapanış videosunu `config.json` dosyasındaki `closing_video_path` değerini değiştirerek özelleştirebilirsiniz.

## Yeni Özellikler

### Anahtar Kelime Öncelikli Video Seçimi

Son güncelleme ile birlikte, video seçim algoritması iyileştirildi. Artık sistem, ana konuyla ilgili videoları öncelikli olarak seçiyor. Örneğin, kedi videoları hakkında bir içerik oluşturduğunuzda, final videoda mutlaka kedi videoları yer alacak.

## Sorun Giderme

**S: FFmpeg ile ilgili hatalar alıyorum.**  
C: FFmpeg'in doğru kurulduğundan ve yolunun `config.json` dosyasında doğru belirtildiğinden emin olun.

**S: OpenAI API ile ilgili hatalar alıyorum.**  
C: API anahtarınızın doğru olduğunu ve yeterli krediye sahip olduğunu kontrol edin.

**S: Video oluşturma çok yavaş.**  
C: Video işleme, bilgisayarınızın gücüne bağlıdır. Daha hızlı bir işlem için düşük çözünürlüklü videolar kullanmayı düşünebilirsiniz.

## Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Daha fazla bilgi için LICENSE dosyasına bakın.

## Teşekkürler

- OpenAI - GPT-4o ve TTS API'leri için
- Pexels - Video içerikleri için
- FFmpeg - Video işleme için
