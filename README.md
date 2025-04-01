# MMoto - Otomatik Video İçerik Oluşturucu

MMoto, metin tabanlı girdileri kullanarak otomatik video içeriği oluşturan bir Python uygulamasıdır. GPT API ve Pexels API kullanarak, verilen konu hakkında metinler oluşturur ve bu metinlere uygun videolar bulup birleştirir.

## Özellikler

- OpenAI API ile içerik üretimi
- Pexels API ile video arama
- Otomatik video işleme ve birleştirme
- Text-to-Speech (TTS) ile ses oluşturma
- Altyazı ekleme
- Otomatik ses-video senkronizasyonu
- Kapanış sahnesi ekleme

## Kurulum

1. Depoyu klonlayın:
```bash
git clone https://github.com/username/MMoto.git
cd MMoto
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. Gerekli API anahtarlarını ayarlayın:
- OpenAI API key
- Pexels API key
- (isteğe bağlı: YouTube API key)

## Kullanım

```bash
python main.py
```

veya

```bash
echo "Video Konusu" | python main.py
```

## Dosya Yapısı

- `main.py`: Ana uygulama
- `modules/`: İşlevsel modüller
  - `content_generator.py`: İçerik oluşturma
  - `video_fetcher.py`: Video arama
  - `video_processor.py`: Video işleme
  - `audio_generator.py`: Ses oluşturma
  - `subtitle_generator.py`: Altyazı oluşturma
  - `closing_scene_adder.py`: Kapanış sahnesi ekleme
- `assets/`: Sabit varlıklar (logo, kapanış sahnesi, vb.)
- `output/`: Oluşturulan içerikler

## Lisans

MIT Lisansı altında dağıtılmaktadır.

## Katkı

Katkıda bulunmak isteyenler için pull request'ler açıktır.
