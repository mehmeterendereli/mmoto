#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from datetime import datetime

def create_project_folder() -> str:
    """
    Yeni bir proje klasörü oluşturur
    
    Returns:
        str: Oluşturulan klasörün tam yolu
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    project_folder = os.path.join("output", f"video_{timestamp}")
    
    # Ana klasörü oluştur
    os.makedirs(project_folder, exist_ok=True)
    
    # Alt klasörleri oluştur
    os.makedirs(os.path.join(project_folder, "pexels_videos"), exist_ok=True)
    os.makedirs(os.path.join(project_folder, "tts_audio"), exist_ok=True)
    
    # Boş dosyaları oluştur
    with open(os.path.join(project_folder, "metadata.json"), "w", encoding="utf-8") as f:
        f.write("{}")
    
    with open(os.path.join(project_folder, "error_log.txt"), "w", encoding="utf-8") as f:
        f.write("")
    
    return project_folder 