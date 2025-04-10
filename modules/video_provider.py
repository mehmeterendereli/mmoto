#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class VideoProvider(ABC):
    """
    Video sağlayıcıları için soyut temel sınıf.
    Tüm video sağlayıcıları (Pexels, Pixabay vb.) bu sınıfı uygulamalıdır.
    """
    
    @abstractmethod
    async def search_videos(self, keywords: List[str], topic: str, content: List[str], language: str = "tr") -> List[Dict[str, Any]]:
        """
        Anahtar kelimelere göre video arama
        
        Args:
            keywords (List[str]): Aranacak anahtar kelimeler
            topic (str): Video konusu
            content (List[str]): Video içeriği
            language (str): Dil kodu (tr, en vb.)
            
        Returns:
            List[Dict[str, Any]]: Video bilgilerini içeren liste
        """
        pass
    
    @abstractmethod
    async def download_videos(self, videos: List[Dict[str, Any]], project_folder: str, min_score: float = 5.0) -> List[str]:
        """
        Videoları indir ve değerlendirme puanına göre sırala
        
        Args:
            videos (List[Dict[str, Any]]): İndirilecek video bilgileri
            project_folder (str): Proje klasörü
            min_score (float): Minimum kabul edilebilir puan
            
        Returns:
            List[str]: İndirilen video dosyalarının yolları
        """
        pass
    
    @abstractmethod
    async def fetch_videos(self, keywords: List[str], topic: str, content: List[str], 
                          project_folder: str, min_score: float = 5.0, 
                          language: str = "tr") -> List[str]:
        """
        Anahtar kelimelere göre video ara ve indir
        
        Args:
            keywords (List[str]): Aranacak anahtar kelimeler
            topic (str): Video konusu
            content (List[str]): Video içeriği
            project_folder (str): Proje klasörü
            min_score (float): Minimum kabul edilebilir puan
            language (str): Dil kodu
            
        Returns:
            List[str]: İndirilen video dosyalarının yolları
        """
        pass 