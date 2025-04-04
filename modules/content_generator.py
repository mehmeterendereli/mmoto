#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import openai
from openai import OpenAI
import re
from typing import Dict, Any

def generate_content(topic: str, language: str = "tr") -> Dict[str, Any]:
    """
    Generates informative text content for a given topic
    
    Args:
        topic (str): Content topic
        language (str): Content language (default: "tr" for Turkish)
    
    Returns:
        Dict[str, Any]: Generated content information
    """
    # Get OpenAI API key from configuration file
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    api_key = ""
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                api_key = config.get("openai_api_key", "")
        except:
            pass
    
    if not api_key:
        print("Warning: OpenAI API key not found!")
        # Return dummy content based on language
        dummy_content = {
            "tr": [
                "Bu örnek bir içeriktir.",
                f"{topic} hakkında bilgi bulunamadı.",
                "Lütfen API anahtarınızı kontrol edin."
            ],
            "en": [
                "This is a sample content.",
                f"No information found about {topic}.",
                "Please check your API key."
            ],
            "es": [
                "Este es un contenido de ejemplo.",
                f"No se encontró información sobre {topic}.",
                "Por favor, verifica tu clave API."
            ],
            "de": [
                "Dies ist ein Beispielinhalt.",
                f"Keine Informationen über {topic} gefunden.",
                "Bitte überprüfen Sie Ihren API-Schlüssel."
            ],
            "fr": [
                "Ceci est un exemple de contenu.",
                f"Aucune information trouvée sur {topic}.",
                "Veuillez vérifier votre clé API."
            ]
        }
        
        # Default to English if language not supported
        selected_language = language if language in dummy_content else "en"
        
        return {
            "topic": topic,
            "response": dummy_content[selected_language]
        }
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Set language-specific settings
        lang_settings = {
            "tr": {
                "system_message": "Kısa ve bilgilendirici içerikler üreten bir asistansın.",
                "prompt_template": f"""
                {topic} hakkında kısa, bilgilendirici bir metin yaz.
                Bu metin bir video için TTS tarafından seslendirilecek.
                
                Önemli Kurallar:
                1. Metin doğrudan konuya girmeli, "merhaba, bugün ... hakkında konuşacağım" gibi gereksiz girişler olmamalı
                2. Her cümle ayrı bir paragraf olmalı, liste veya numaralandırılmış öğeler kullanma
                3. Toplam 7 cümle ve tüm metin seslendirildiğinde yaklaşık 45 saniye sürmelidir (ASLA 50 saniyeyi geçmemeli)
                4. Her cümle anlamlı ve eğitici olmalı
                5. Hedef kitle genel izleyiciler, bu nedenle teknik olmayan bir dil kullan
                6. Her cümle 12-20 kelime uzunluğunda ve Türkçe olmalı
                7. Metin sadece düz cümlelerden oluşmalı, toplamda sadece 7 cümle
                8. Her cümle doğal olması için 2-4 saniyelik nefes alma molaları içermeli
                
                Lütfen yukarıdaki kurallara tamamen uyan, TTS tarafından okunduğunda 35-45 saniye sürecek toplam 7 cümlelik bir metin oluştur.
                Her cümleyi ayrı bir paragraf olarak sağla.
                """
            },
            "en": {
                "system_message": "You are an assistant that creates short, informative content.",
                "prompt_template": f"""
                Write a short, informative text about {topic}.
                This text will be narrated by TTS for a video.
                
                Important Rules:
                1. The text should get straight to the point, no unnecessary introductions like "hello, today I'll talk about..."
                2. Each sentence should be a separate paragraph, no lists or numbered items
                3. Total of 7 sentences and the entire text should take approximately 45 seconds when narrated (NEVER exceed 50 seconds)
                4. Each sentence should be meaningful and educational
                5. Target audience is general viewers, so use non-technical language
                6. Each sentence should be between 12-20 words in length and in English
                7. The text should consist of only plain sentences, just 7 sentences in total
                8. Each sentence should include a 2-4 second breathing pause (for naturalness)
                
                Please create a text that fully complies with the above rules, with a total of 7 sentences that will take 35-45 seconds when read by TTS.
                Provide each sentence as a separate paragraph.
                """
            },
            "es": {
                "system_message": "Eres un asistente que crea contenido breve e informativo.",
                "prompt_template": f"""
                Escribe un texto breve e informativo sobre {topic}.
                Este texto será narrado por TTS para un video.
                
                Reglas importantes:
                1. El texto debe ir directo al punto, sin introducciones innecesarias como "hola, hoy hablaré sobre..."
                2. Cada oración debe ser un párrafo separado, sin listas ni elementos numerados
                3. Un total de 7 oraciones y todo el texto debe tomar aproximadamente 45 segundos cuando se narra (NUNCA exceder los 50 segundos)
                4. Cada oración debe ser significativa y educativa
                5. El público objetivo son espectadores generales, por lo que usa un lenguaje no técnico
                6. Cada oración debe tener entre 12-20 palabras de longitud y en español
                7. El texto debe consistir solo en oraciones simples, solo 7 oraciones en total
                8. Cada oración debe incluir una pausa de respiración de 2-4 segundos (para naturalidad)
                
                Por favor, crea un texto que cumpla completamente con las reglas anteriores, con un total de 7 oraciones que tomarán 35-45 segundos cuando sean leídas por TTS.
                Proporciona cada oración como un párrafo separado.
                """
            }
        }
        
        # Default to English if language not supported
        selected_language = language if language in lang_settings else "en"
        
        # Get language settings
        settings = lang_settings[selected_language]
        
        # Send request
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": settings["system_message"]},
                {"role": "user", "content": settings["prompt_template"]}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Get and process the response
        content = response.choices[0].message.content
        
        # Split the response into sentences - each paragraph is a sentence
        sentences = []
        for paragraph in content.strip().split('\n'):
            paragraph = paragraph.strip()
            if paragraph:  # Skip empty paragraphs
                # Remove bullet points and numbers if present
                cleaned = re.sub(r'^\d+\.\s*|\*\s*|\-\s*', '', paragraph)
                sentences.append(cleaned)
        
        # Check sentence count and adjust if needed
        if len(sentences) > 7:
            sentences = sentences[:7]  # Maximum 7 sentences
        
        # Return results
        return {
            "topic": topic,
            "response": sentences
        }
    
    except Exception as e:
        print(f"Content generation error: {str(e)}")
        # Return dummy content in case of error
        dummy_messages = {
            "tr": [
                f"{topic} hakkında içerik oluşturulurken bir hata oluştu.",
                "API ile iletişimde bir sorun oluştu.",
                "Lütfen daha sonra tekrar deneyin."
            ],
            "en": [
                f"An error occurred while creating content about {topic}.",
                "There was a problem communicating with the API.",
                "Please try again later."
            ],
            "es": [
                f"Ocurrió un error al crear contenido sobre {topic}.",
                "Hubo un problema al comunicarse con la API.",
                "Por favor, inténtelo de nuevo más tarde."
            ]
        }
        
        # Default to English if language not supported
        selected_language = language if language in dummy_messages else "en"
        
        return {
            "topic": topic,
            "response": dummy_messages[selected_language]
        } 