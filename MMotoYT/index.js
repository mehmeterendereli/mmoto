require('dotenv').config();
const fs = require('fs');
const path = require('path');
const express = require('express');
const { google } = require('googleapis');
const open = require('open');

const app = express();
const port = 3000;

// OAuth2 yapılandırması
const oauth2Client = new google.auth.OAuth2(
  process.env.CLIENT_ID,
  process.env.CLIENT_SECRET,
  process.env.REDIRECT_URI
);

// YouTube API'sini yapılandırma
const youtube = google.youtube({
  version: 'v3',
  auth: oauth2Client
});

// OAuth2 için izin kapsamları
const SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube'];

// Token'ı kaydetmek için
let tokens = null;

try {
  if (fs.existsSync('./tokens.json')) {
    tokens = JSON.parse(fs.readFileSync('./tokens.json'));
    oauth2Client.setCredentials(tokens);
    console.log('Kayıtlı token bulundu, otomatik olarak giriş yapıldı.');
    startUploadProcess();
  } else {
    // Yetkilendirme URL'si oluştur
    const authUrl = oauth2Client.generateAuthUrl({
      access_type: 'offline',
      scope: SCOPES,
      prompt: 'consent'
    });
    
    console.log('YouTube hesabınıza giriş yapmanız gerekiyor. Tarayıcı açılacak...');
    open(authUrl);
  }
} catch (error) {
  console.error('Token okuma hatası:', error);
}

// Express routes
app.get('/oauth2callback', async (req, res) => {
  const { code } = req.query;
  
  try {
    // Token alma
    const { tokens: newTokens } = await oauth2Client.getToken(code);
    oauth2Client.setCredentials(newTokens);
    
    // Token'ları kaydet
    fs.writeFileSync('./tokens.json', JSON.stringify(newTokens));
    console.log('Yetkilendirme başarılı! Token kaydedildi.');
    
    res.send('Yetkilendirme tamamlandı! Bu pencereyi kapatabilirsiniz.');
    
    startUploadProcess();
  } catch (error) {
    console.error('Yetkilendirme hatası:', error);
    res.status(500).send('Yetkilendirme sırasında bir hata oluştu: ' + error.message);
  }
});

app.listen(port, () => {
  console.log(`Server başlatıldı: http://localhost:${port}`);
});

async function startUploadProcess() {
  try {
    // Video klasörünü kontrol et
    const videosDir = process.env.VIDEOS_DIR;
    if (!fs.existsSync(videosDir)) {
      fs.mkdirSync(videosDir, { recursive: true });
      console.log(`${videosDir} klasörü oluşturuldu.`);
    }
    
    // Videonun var olup olmadığını kontrol et
    const files = fs.readdirSync(videosDir);
    const videoFiles = files.filter(file => {
      const ext = path.extname(file).toLowerCase();
      return ['.mp4', '.avi', '.mov', '.mkv', '.wmv'].includes(ext);
    });
    
    if (videoFiles.length === 0) {
      console.log(`${videosDir} klasöründe video bulunamadı. Lütfen video ekleyin ve tekrar deneyin.`);
      return;
    }
    
    console.log(`${videoFiles.length} video bulundu. Yükleme işlemi başlıyor...`);
    
    for (const videoFile of videoFiles) {
      await uploadVideo(path.join(videosDir, videoFile));
    }
  } catch (error) {
    console.error('Video yükleme hatası:', error);
  }
}

async function uploadVideo(videoPath) {
  try {
    const fileName = path.basename(videoPath);
    const fileSize = fs.statSync(videoPath).size;
    
    // Varsayılan video bilgileri (dosya adından alınır)
    const videoTitle = path.parse(fileName).name;
    const videoDescription = `Açıklama: ${videoTitle}`;
    
    // Metadata dosyasını kontrol et
    const metadataPath = videoPath + '.json';
    let videoMetadata = {
      title: videoTitle,
      description: videoDescription,
      tags: [],
      categoryId: '22', // İnsanlar ve Bloglar
      privacyStatus: 'private' // Başlangıçta özel olarak yükle
    };
    
    if (fs.existsSync(metadataPath)) {
      try {
        const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
        videoMetadata = { ...videoMetadata, ...metadata };
      } catch (e) {
        console.warn(`Metadata dosyası ${metadataPath} okunamadı:`, e);
      }
    }
    
    console.log(`"${videoMetadata.title}" yükleniyor... (${(fileSize / 1024 / 1024).toFixed(2)} MB)`);
    
    const res = await youtube.videos.insert({
      part: 'snippet,status',
      requestBody: {
        snippet: {
          title: videoMetadata.title,
          description: videoMetadata.description,
          tags: videoMetadata.tags,
          categoryId: videoMetadata.categoryId,
          defaultLanguage: 'tr'
        },
        status: {
          privacyStatus: videoMetadata.privacyStatus
        }
      },
      media: {
        body: fs.createReadStream(videoPath)
      }
    });
    
    console.log(`Yükleme tamamlandı! Video ID: ${res.data.id}`);
    console.log(`Video URL: https://youtu.be/${res.data.id}`);
    
    // Başarılı yüklemeden sonra video dosyasını yüklenenler klasörüne taşı
    const uploadedDir = path.join(process.env.VIDEOS_DIR, 'uploaded');
    if (!fs.existsSync(uploadedDir)) {
      fs.mkdirSync(uploadedDir, { recursive: true });
    }
    
    const newPath = path.join(uploadedDir, fileName);
    fs.renameSync(videoPath, newPath);
    
    // Metadata dosyasını da taşı (varsa)
    if (fs.existsSync(metadataPath)) {
      fs.renameSync(metadataPath, path.join(uploadedDir, path.basename(metadataPath)));
    }
    
    console.log(`"${fileName}" 'uploaded' klasörüne taşındı.`);
    return res.data.id;
  } catch (error) {
    console.error('Video yükleme hatası:', error.message);
    if (error.errors) {
      console.error('API Hataları:', JSON.stringify(error.errors, null, 2));
    }
    throw error;
  }
}

// Ctrl+C ile kapatmayı ele al
process.on('SIGINT', () => {
  console.log('Program kapatılıyor...');
  process.exit(0);
}); 