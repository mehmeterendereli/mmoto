"""
English language file
"""

LANG = {
    # Main interface elements
    "app_title": "MMoto Video Creator",
    "ready": "Ready",
    "working": "Working...",
    "error": "Error",
    
    # Menu
    "home": "Home",
    "api_keys": "API Keys",
    "settings": "Settings",
    "appearance": "Appearance:",
    
    # Home page
    "topic": "Topic:",
    "generate_topic": "Generate Topic",
    "log_title": "Process Log:",
    "continuous_mode": "Continuous Mode",
    "upload_to_youtube": "Upload to YouTube?",
    "language": "Language:",
    "turkish": "Turkish",
    "english": "English",
    "max_videos": "Maximum Videos:",
    "status": "Status:",
    "start": "Start",
    "stop": "Stop",
    "check_youtube": "Check YouTube Settings",
    
    # Settings page
    "ui_language": "Interface Language:",
    "content_language": "Content Language:",
    "tts_language": "TTS Language:",
    "subtitle_language": "Subtitle Language:",
    "content_and_tts_language": "Content and TTS Language:",
    "tts_voice_model": "TTS Voice Model:",
    "content_language_info": "The selected UI language only determines the language of the interface and does not affect the videos. The content language determines which language the videos will be created in. Content and TTS languages should generally be the same, but you can select a different language for subtitles. Please click the 'Save Settings' button for your changes to take effect.",
    "select_language": "Select Language",
    
    # Supported languages
    "lang_tr": "Turkish",
    "lang_en": "English",
    "lang_es": "Spanish",
    "lang_fr": "French",
    "lang_de": "German",
    "lang_it": "Italian",
    "lang_pt": "Portuguese",
    "lang_ru": "Russian",
    "lang_zh": "Chinese",
    "lang_ja": "Japanese",
    "lang_ko": "Korean",
    "lang_ar": "Arabic",
    
    # API Keys page
    "api_title": "API Keys",
    "openai_api": "OpenAI API Key:",
    "pexels_api": "Pexels API Key:",
    "youtube_api": "YouTube API Key:",
    "pixabay_api": "Pixabay API Key:",
    "show_keys": "Show API Keys",
    "save_settings": "Save Settings",
    "settings_saved": "Settings successfully saved!",
    
    # Process messages
    "process_started": "Process started",
    "process_completed": "Process completed",
    "process_stopped": "Process stopped",
    "continuous_mode_enabled": "Continuous mode enabled",
    "continuous_mode_disabled": "Continuous mode disabled",
    "new_topic_generated": "New topic generated",
    "auto_generating_topic": "Automatically generating topic...",
    "preparing_next_video": "Preparing for next video...",
    "content_language_changed": "Content language changed",
    "content_and_tts_language_changed": "Content and TTS language changed",
    "tts_language_changed": "TTS language changed",
    "subtitle_language_changed": "Subtitle language changed",
    "warning_default_language": "Using default language because content language was not specified",
    "warning_tts_language_set": "TTS language set to be the same as content language",
    "warning_subtitle_language_set": "Subtitle language set to be the same as content language",
    "using_content_language": "Using content language",
    "using_content_and_tts_language": "Using content and TTS language",
    "using_tts_language": "Using TTS language",
    "using_subtitle_language": "Using subtitle language",
    
    # YouTube settings
    "youtube_settings_ok": "YouTube settings checked and no issues found",
    "error_no_youtube_key": "YouTube API key not found",
    "error_no_client_secrets": "client_secrets.json file not found",
    "youtube_setup_instructions": "To use YouTube API, you need to create a client_secrets.json file. For detailed information, visit Google Cloud Console.",
    
    # Error messages
    "error_no_topic": "Please enter or generate a topic",
    "error_already_running": "Process is already running",
    "error_no_openai_key": "OpenAI API key not found",
    "error_during_process": "Error occurred during process",
    
    # Help titles
    "openai_help_title": "How to Get OpenAI API Key",
    "pexels_help_title": "How to Get Pexels API Key",
    "youtube_help_title": "How to Get YouTube API Key",
    "pixabay_help_title": "How to Get Pixabay API Key",
    
    # Help contents
    "openai_help_content": "Follow these steps to get an OpenAI API Key:\n\n"
                          "1. Log in to your OpenAI account (or sign up)\n"
                          "2. Click on the profile menu in the top right corner\n"
                          "3. Select 'View API Keys'\n"
                          "4. Click on 'Create new secret key' button\n"
                          "5. Copy the generated key and paste it in this field\n\n"
                          "NOTE: Your API key starts with 'sk-...' and is approximately 50 characters long.",
    
    "pexels_help_content": "Follow these steps to get a Pexels API Key:\n\n"
                          "1. Log in to your Pexels account (or sign up)\n"
                          "2. Go to https://www.pexels.com/api/new/\n"
                          "3. Copy your key from the 'Your API Key' section\n"
                          "4. Paste the copied key into this field\n\n"
                          "NOTE: Pexels API key is approximately 30-40 characters long.",
    
    "youtube_help_content": "Follow these steps to get a YouTube API Key:\n\n"
                           "1. Log in to Google Cloud Console\n"
                           "2. Create a project (if you don't have one)\n"
                           "3. Enable YouTube Data API v3 from the API Library\n"
                           "4. Create an API key from the Credentials menu\n"
                           "5. Paste the created key into this field\n\n"
                           "NOTE: YouTube API key starts with 'AIzaSy...'.",
    
    "pixabay_help_content": "Follow these steps to get a Pixabay API Key:\n\n"
                           "1. Log in to your Pixabay account (or sign up)\n"
                           "2. Go to https://pixabay.com/api/docs/\n"
                           "3. Fill out the 'API Key Request' section at the bottom of the page\n"
                           "4. Paste the API key you received in the confirmation email into this field\n\n"
                           "NOTE: Pixabay API key is 15-20 characters long consisting of numbers and letters.",
    
    # Help links
    "openai_help_link": "Go to OpenAI API Keys Page",
    "pexels_help_link": "Go to Pexels API Page",
    "youtube_help_link": "Go to Google Cloud Console",
    "pixabay_help_link": "Go to Pixabay API Page",
    
    # Other
    "close": "Close",
    "error_prefix": "Error: "
} 