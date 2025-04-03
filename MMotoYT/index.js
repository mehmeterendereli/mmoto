require('dotenv').config();
const fs = require('fs');
const path = require('path');
const express = require('express');
const { google } = require('googleapis');
const open = require('open');

// Set auto-exit timeout (10 seconds)
const AUTO_EXIT_TIMEOUT = 10000;

// Auto-exit function
function scheduleExit() {
  console.log(`\nScheduling automatic exit in ${AUTO_EXIT_TIMEOUT/1000} seconds...`);
  setTimeout(() => {
    console.log('Auto-exiting process');
    process.exit(0);
  }, AUTO_EXIT_TIMEOUT);
}

const app = express();
const port = 3000;

// Close the server and exit on completion
function shutdownServer() {
  console.log('Shutting down server...');
  server.close(() => {
    console.log('Server closed. Exiting process.');
    scheduleExit();
  });
}

// OAuth2 configuration
const oauth2Client = new google.auth.OAuth2(
  process.env.CLIENT_ID,
  process.env.CLIENT_SECRET,
  process.env.REDIRECT_URI
);

// Configure YouTube API
const youtube = google.youtube({
  version: 'v3',
  auth: oauth2Client
});

// OAuth2 permission scopes
const SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube'];

// For saving tokens
let tokens = null;

try {
  if (fs.existsSync('./tokens.json')) {
    tokens = JSON.parse(fs.readFileSync('./tokens.json'));
    oauth2Client.setCredentials(tokens);
    console.log('Saved token found, logged in automatically.');
    startUploadProcess().then(() => {
      console.log('Upload process completed, closing application...');
      shutdownServer();
    }).catch(err => {
      console.error('Error during upload process:', err);
      shutdownServer();
    });
  } else {
    // Create authorization URL
    const authUrl = oauth2Client.generateAuthUrl({
      access_type: 'offline',
      scope: SCOPES,
      prompt: 'consent'
    });
    
    console.log('You need to log in to your YouTube account. Browser will open...');
    open(authUrl);
  }
} catch (error) {
  console.error('Token reading error:', error);
  scheduleExit();
}

// Express routes
app.get('/oauth2callback', async (req, res) => {
  const { code } = req.query;
  
  try {
    // Get token
    const { tokens: newTokens } = await oauth2Client.getToken(code);
    oauth2Client.setCredentials(newTokens);
    
    // Save tokens
    fs.writeFileSync('./tokens.json', JSON.stringify(newTokens));
    console.log('Authorization successful! Token saved.');
    
    res.send('Authorization complete! You can close this window.');
    
    await startUploadProcess();
    shutdownServer();
  } catch (error) {
    console.error('Authorization error:', error);
    res.status(500).send('An error occurred during authorization: ' + error.message);
    scheduleExit();
  }
});

// Store server reference so we can close it later
const server = app.listen(port, () => {
  console.log(`Server started: http://localhost:${port}`);
});

async function startUploadProcess() {
  try {
    // Check the video folder
    const videosDir = process.env.VIDEOS_DIR;
    if (!fs.existsSync(videosDir)) {
      fs.mkdirSync(videosDir, { recursive: true });
      console.log(`Created ${videosDir} directory.`);
    }
    
    let processedAnyVideo = false;
    
    // Check videos in the videos directory (optional)
    if (process.env.CHECK_VIDEOS_DIR === 'true') {
      const files = fs.readdirSync(videosDir);
      const videoFiles = files.filter(file => {
        const ext = path.extname(file).toLowerCase();
        return ['.mp4', '.avi', '.mov', '.mkv', '.wmv'].includes(ext);
      });
      
      if (videoFiles.length > 0) {
        console.log(`Found ${videoFiles.length} videos in ${videosDir}. Starting upload...`);
        
        // Process only the most recent video file
        const mostRecentVideo = videoFiles
          .map(file => ({ file, mtime: fs.statSync(path.join(videosDir, file)).mtime }))
          .sort((a, b) => b.mtime - a.mtime)[0].file;
        
        console.log(`Processing most recent video: ${mostRecentVideo}`);
        await uploadVideo(path.join(videosDir, mostRecentVideo));
        processedAnyVideo = true;
      }
    }
    
    // Check for videos in the output directory
    const outputDir = path.resolve(__dirname, '../output');
    let outputVideoFolders = [];
    
    if (fs.existsSync(outputDir)) {
      const folderItems = fs.readdirSync(outputDir);
      outputVideoFolders = folderItems
        .filter(item => item.startsWith('video_'))
        .map(folder => path.join(outputDir, folder))
        .filter(folderPath => fs.statSync(folderPath).isDirectory())
        .sort((a, b) => fs.statSync(b).mtime.getTime() - fs.statSync(a).mtime.getTime()); // Sort newest first
    }
    
    // Process only the most recent video folder
    if (outputVideoFolders.length > 0) {
      // Get the most recent folder (it's already sorted)
      const mostRecentFolder = outputVideoFolders[0];
      console.log(`Found ${outputVideoFolders.length} video folders. Processing only the most recent one: ${path.basename(mostRecentFolder)}`);
      
      const finalVideoPath = path.join(mostRecentFolder, 'final_video.mp4');
      const metadataPath = path.join(mostRecentFolder, 'metadata.json');
      
      if (fs.existsSync(finalVideoPath)) {
        console.log(`Found final video in ${path.basename(mostRecentFolder)}`);
        
        // Check if this video was already uploaded
        const uploadMarkPath = path.join(mostRecentFolder, 'uploaded.txt');
        if (fs.existsSync(uploadMarkPath)) {
          console.log(`Video in ${path.basename(mostRecentFolder)} was already uploaded. Skipping.`);
        } else {
          // Process the metadata file if it exists
          let metadata = null;
          if (fs.existsSync(metadataPath)) {
            try {
              metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
              console.log(`Loaded metadata from ${path.basename(metadataPath)}`);
            } catch (e) {
              console.warn(`Could not read metadata file ${metadataPath}:`, e);
            }
          }
          
          // Upload the video
          const videoId = await uploadVideoWithMetadata(finalVideoPath, metadata);
          
          // Mark as uploaded
          if (videoId) {
            fs.writeFileSync(uploadMarkPath, `Uploaded on: ${new Date().toISOString()}\nVideo ID: ${videoId}\nVideo URL: https://youtu.be/${videoId}\nShorts URL: https://youtube.com/shorts/${videoId}`);
            console.log(`Marked ${path.basename(mostRecentFolder)} as uploaded.`);
            processedAnyVideo = true;
          }
        }
      } else {
        console.log(`No final video found in the most recent folder: ${path.basename(mostRecentFolder)}`);
      }
    } else {
      console.log(`No video folders found in the output directory.`);
    }
    
    if (!processedAnyVideo) {
      console.log(`No videos found to upload. Please add videos to the ${videosDir} directory or generate new videos.`);
    } else {
      console.log('All video processing complete!');
    }
    
    // Ensure server is closed and process exits
    return true;
  } catch (error) {
    console.error('Video upload error:', error);
    return false;
  }
}

async function uploadVideoWithMetadata(videoPath, metadata) {
  try {
    const fileName = path.basename(videoPath);
    const fileSize = fs.statSync(videoPath).size;
    
    // Default video information
    let videoMetadata = {
      title: path.parse(fileName).name,
      description: `Description: ${path.parse(fileName).name}`,
      tags: [],
      categoryId: '27', // Education by default
      privacyStatus: 'public' // Upload as public by default
    };
    
    // If metadata provided, use it
    if (metadata) {
      console.log('Using metadata from metadata.json file');
      
      // Use proper fields from our metadata format
      if (metadata.title) videoMetadata.title = metadata.title;
      if (metadata.content) videoMetadata.description = metadata.content;
      if (metadata.keywords && Array.isArray(metadata.keywords)) {
        videoMetadata.tags = metadata.keywords.map(tag => String(tag)); // Ensure all tags are strings
      }
      if (metadata.category_id) videoMetadata.categoryId = metadata.category_id;
      
      // Log metadata being used
      console.log(`Title: ${videoMetadata.title}`);
      console.log(`Category: ${videoMetadata.categoryId}`);
      console.log(`Tags count: ${videoMetadata.tags.length}`);
    }
    
    return await uploadVideo(videoPath, videoMetadata);
  } catch (error) {
    console.error(`Error preparing video upload for ${videoPath}:`, error.message);
    return null;
  }
}

async function uploadVideo(videoPath, customMetadata = null) {
  try {
    const fileName = path.basename(videoPath);
    const fileSize = fs.statSync(videoPath).size;
    
    // Default video information (based on filename)
    const videoTitle = path.parse(fileName).name;
    const videoDescription = `Description: ${videoTitle}`;
    
    // Check for metadata file
    const metadataPath = videoPath + '.json';
    let videoMetadata = {
      title: videoTitle,
      description: videoDescription,
      tags: [],
      categoryId: '27', // Education by default
      privacyStatus: 'public' // Upload as public by default
    };
    
    // If custom metadata provided, use it
    if (customMetadata) {
      videoMetadata = { ...videoMetadata, ...customMetadata };
    }
    // Otherwise check for metadata file
    else if (fs.existsSync(metadataPath)) {
      try {
        const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
        videoMetadata = { ...videoMetadata, ...metadata };
      } catch (e) {
        console.warn(`Could not read metadata file ${metadataPath}:`, e);
      }
    }
    
    console.log(`Uploading "${videoMetadata.title}"... (${(fileSize / 1024 / 1024).toFixed(2)} MB)`);
    
    // Ensure we don't exceed YouTube's tag limit (500 characters total)
    const tagsTotalLength = videoMetadata.tags.reduce((total, tag) => total + String(tag).length, 0);
    if (tagsTotalLength > 490) {
      console.log('Tags exceed YouTube limit, truncating...');
      let currentTotal = 0;
      const limitedTags = [];
      
      for (const tag of videoMetadata.tags) {
        if (currentTotal + String(tag).length < 490) {
          limitedTags.push(tag);
          currentTotal += String(tag).length;
        } else {
          break;
        }
      }
      
      videoMetadata.tags = limitedTags;
      console.log(`Using ${videoMetadata.tags.length} tags (${currentTotal} characters)`);
    }
    
    // Ensure we don't exceed YouTube's title limit (100 characters)
    if (videoMetadata.title.length > 100) {
      videoMetadata.title = videoMetadata.title.substring(0, 97) + '...';
      console.log(`Title too long, truncated to: ${videoMetadata.title}`);
    }
    
    // Ensure we don't exceed YouTube's description limit (5000 characters)
    if (videoMetadata.description.length > 5000) {
      videoMetadata.description = videoMetadata.description.substring(0, 4997) + '...';
      console.log('Description too long, truncated');
    }
    
    const res = await youtube.videos.insert({
      part: 'snippet,status',
      requestBody: {
        snippet: {
          title: videoMetadata.title,
          description: videoMetadata.description,
          tags: videoMetadata.tags,
          categoryId: videoMetadata.categoryId,
          defaultLanguage: 'en'
        },
        status: {
          privacyStatus: videoMetadata.privacyStatus
        }
      },
      media: {
        body: fs.createReadStream(videoPath)
      }
    });
    
    console.log(`Upload complete! Video ID: ${res.data.id}`);
    console.log(`Video URL: https://youtu.be/${res.data.id}`);
    console.log(`Shorts URL: https://youtube.com/shorts/${res.data.id}`);
    
    // Move video file to uploaded folder after successful upload
    if (!customMetadata) { // Only move if it's from the videos directory
      const uploadedDir = path.join(process.env.VIDEOS_DIR, 'uploaded');
      if (!fs.existsSync(uploadedDir)) {
        fs.mkdirSync(uploadedDir, { recursive: true });
      }
      
      const newPath = path.join(uploadedDir, fileName);
      fs.renameSync(videoPath, newPath);
      
      // Move metadata file too (if exists)
      if (fs.existsSync(metadataPath)) {
        fs.renameSync(metadataPath, path.join(uploadedDir, path.basename(metadataPath)));
      }
      
      console.log(`"${fileName}" moved to 'uploaded' folder.`);
    }
    
    return res.data.id;
  } catch (error) {
    console.error('Video upload error:', error.message);
    if (error.errors) {
      console.error('API Errors:', JSON.stringify(error.errors, null, 2));
    }
    throw error;
  }
}

// Handle shutdown with Ctrl+C
process.on('SIGINT', () => {
  console.log('Program closing...');
  process.exit(0);
});

// Add an automatic exit timeout as a failsafe
setTimeout(() => {
  console.log('Exit timeout reached. Forcing process exit.');
  process.exit(0);
}, 5 * 60 * 1000);  // 5 minutes max runtime 