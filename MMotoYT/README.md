# YouTube Otomatik Video Yükleyici

Bu uygulama, YouTube Data API v3 kullanarak videolarınızı otomatik olarak YouTube kanalınıza yükler.

## Özellikler

- OAuth2 ile YouTube hesabınıza güvenli şekilde bağlanma
- Belirtilen klasördeki tüm videoları otomatik olarak yükleme
- Her video için özel metadata tanımlama imkanı
- Yüklenen videoları ayrı bir klasöre taşıma
- Yükleme durumunu ve hataları izleme

## Kurulum

1. Node.js'i yükleyin (https://nodejs.org/)
2. Bu repo'yu bilgisayarınıza indirin
3. Terminal'de repo klasörüne gidip şu komutu çalıştırın:
   ```
   npm install
   ```
4. `.env` dosyasını düzenleyin:
   - Google Cloud Console'dan bir proje oluşturun
   - YouTube Data API v3'ü etkinleştirin
   - OAuth 2.0 istemci kimliği oluşturun
   - Alınan CLIENT_ID ve CLIENT_SECRET değerlerini .env dosyasına ekleyin
   - İzin verilen yönlendirme URI'sini `http://localhost:3000/oauth2callback` olarak ayarlayın

## Kullanım

1. `.env` dosyasında belirttiğiniz `VIDEOS_DIR` klasörüne video dosyalarını yerleştirin
2. (İsteğe bağlı) Her video için metadata tanımlamak isterseniz, videonun adıyla aynı isimde `.json` uzantılı dosya oluşturun (örn: `video.mp4.json`)
   ```json
   {
     "title": "Video Başlığı",
     "description": "Video açıklaması...",
     "tags": ["etiket1", "etiket2"],
     "categoryId": "22",
     "privacyStatus": "private"
   }
   ```
3. Uygulamayı başlatmak için şu komutu çalıştırın:
   ```
   npm start
   ```
4. İlk çalıştırmada tarayıcıda YouTube hesabınıza giriş yapmanız istenecektir
5. Giriş yaptıktan sonra, uygulama videoları yüklemeye başlayacaktır

## Kategori ID'leri

- `1`: Film ve Animasyon
- `2`: Otomobiller ve Araçlar
- `10`: Müzik
- `15`: Evcil Hayvanlar ve Hayvanlar
- `17`: Spor
- `18`: Kısa Filmler
- `19`: Seyahat ve Etkinlikler
- `20`: Oyun
- `21`: Video Blogu
- `22`: İnsanlar ve Bloglar
- `23`: Komedi
- `24`: Eğlence
- `25`: Haberler ve Politika
- `26`: Nasıl Yapılır ve Stil
- `27`: Eğitim
- `28`: Bilim ve Teknoloji
- `29`: Kar Amacı Gütmeyen ve Aktivizm
- `30`: Filmler
- `31`: Animasyon
- `32`: Aksiyon ve Macera
- `33`: Klasikler
- `34`: Komedi
- `35`: Belgesel
- `36`: Drama
- `37`: Aile
- `38`: Yabancı
- `39`: Korku
- `40`: Bilim Kurgu ve Fantezi
- `41`: Gerilim
- `42`: Kısa Filmler
- `43`: Gösteriler
- `44`: Fragmanlar

## Yük Sınırlamaları

YouTube API'si günlük bir kota sınırı uygular. Bu genellikle günlük 10.000 birimdir ve video yükleme gibi işlemler bu kotayı hızla tüketebilir. Detaylar için: https://developers.google.com/youtube/v3/getting-started#quota 