// Bu dosya, Google Cloud Console'dan indirilen client_secret dosyasından
// gerekli kimlik bilgilerini çıkarmak için kullanılır

const fs = require('fs');

try {
  // JSON dosyasını oku
  const fileName = 'client_secret_537954593746-ceadf2hoapr6mkl05ukcgepmp9rv4jlr.apps.googleusercontent.com.json';
  
  if (!fs.existsSync(fileName)) {
    console.error(`HATA: ${fileName} dosyası bulunamadı.`);
    console.error('Lütfen bu dosyayı projenin ana dizinine kopyalayın.');
    process.exit(1);
  }
  
  const secretData = JSON.parse(fs.readFileSync(fileName, 'utf8'));
  
  if (!secretData.web) {
    console.error('HATA: JSON dosyası beklenen formatta değil.');
    process.exit(1);
  }
  
  // Gerekli bilgileri çıkar
  const clientId = secretData.web.client_id;
  const clientSecret = secretData.web.client_secret;
  
  // .env dosyasının var olup olmadığını kontrol et
  if (!fs.existsSync('.env')) {
    // .env dosyası yoksa oluştur
    const envContent = `# YouTube API Bilgileri
CLIENT_ID=${clientId}
CLIENT_SECRET=${clientSecret}
REDIRECT_URI=http://localhost:3000/oauth2callback

# Video yüklenecek klasör
VIDEOS_DIR=./videos

# Hangi kanalınıza yükleneceği (channel ID)
CHANNEL_ID=YOUR_CHANNEL_ID`;
    
    fs.writeFileSync('.env', envContent);
    console.log('.env dosyası oluşturuldu.');
  } else {
    // .env dosyası varsa, sadece kimlik bilgilerini güncelle
    let envContent = fs.readFileSync('.env', 'utf8');
    
    // CLIENT_ID satırını güncelle veya ekle
    if (envContent.includes('CLIENT_ID=')) {
      envContent = envContent.replace(/CLIENT_ID=.*/, `CLIENT_ID=${clientId}`);
    } else {
      envContent += `\nCLIENT_ID=${clientId}`;
    }
    
    // CLIENT_SECRET satırını güncelle veya ekle
    if (envContent.includes('CLIENT_SECRET=')) {
      envContent = envContent.replace(/CLIENT_SECRET=.*/, `CLIENT_SECRET=${clientSecret}`);
    } else {
      envContent += `\nCLIENT_SECRET=${clientSecret}`;
    }
    
    fs.writeFileSync('.env', envContent);
    console.log('.env dosyası güncellendi.');
  }
  
  console.log('İşlem tamamlandı. CLIENT_ID ve CLIENT_SECRET değerleri .env dosyasına kaydedildi.');
  console.log('ÖNEMLI: Lütfen .env dosyasındaki CHANNEL_ID değerini kendi YouTube kanal ID\'niz ile değiştirin.');
  
} catch (error) {
  console.error('Bir hata oluştu:', error.message);
  process.exit(1);
} 