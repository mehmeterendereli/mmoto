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
                "system_message": "Sen TikTok ve YouTube Shorts için viral içerik üreten bir uzmansın. İnsanların dikkatini hemen çekecek şok edici, merak uyandırıcı ve ilgi çekici içerikler yaratmada ustasın.",
                "prompt_template": f"""
                {topic} hakkında viral olabilecek, ilgi çekici ve merak uyandıran bir içerik yaz.
                Bu içerik YouTube Shorts veya TikTok'ta seslendirilecek.
                
                Kritik Kurallar:
                1. İLK CÜMLE MUTLAKA İZLEYİCİYİ ŞAŞIRTACAK, ŞOK EDECEK veya çok merak uyandıracak bir bilgi/iddia içermeli
                2. İkinci cümle ilk cümledeki şaşırtıcı bilgiyi desteklemeli veya daha da ilginç hale getirmeli
                3. Diğer cümleler ilgi çekici ifadelerle başlamalı
                4. Her cümle ayrı bir paragraf olmalı, liste veya numaralandırılmış öğeler kullanma
                5. Toplam 7 cümle ve tüm metin seslendirildiğinde yaklaşık 45 saniye sürmelidir (ASLA 50 saniyeyi geçmemeli)
                6. Her cümle anlamlı ve eğitici olmalı, fakat abartılı ve dramatik bir dil kullanılmalı
                7. Her cümle 12-20 kelime uzunluğunda ve Türkçe olmalı
                8. İçerik, istatistikler, sayılar ve şaşırtıcı karşılaştırmalar içermeli
                9. Son cümle izleyiciyi şaşırtacak bir bilgi veya düşündürücü bir soru ile bitmelidir
                10. İzleyiciyi ikinci şahıs (sen/siz) olarak adreslemekten çekinme, bu bağlantıyı güçlendirir
                
                Lütfen yukarıdaki kurallara tamamen uyan, TTS tarafından okunduğunda 35-45 saniye sürecek toplam 7 cümlelik bir metin oluştur.
                Her cümleyi ayrı bir paragraf olarak sağla.
                """
            },
            "en": {
                "system_message": "You are an expert creator of viral content for TikTok and YouTube Shorts. You excel at creating shocking, curiosity-inducing and attention-grabbing content that hooks viewers instantly.",
                "prompt_template": f"""
                Write a viral, attention-grabbing text about {topic} that will hook viewers instantly.
                This text will be narrated for YouTube Shorts or TikTok.
                
                Critical Rules:
                1. THE FIRST SENTENCE MUST CONTAIN a SHOCKING fact/claim that will SURPRISE viewers or create extreme curiosity
                2. The second sentence should support the shocking first sentence or make it even more interesting
                3. Other sentences should start with phrases like "but what's really shocking is...", "the hidden truth is...", "what's incredible is..."
                4. Each sentence should be a separate paragraph, no lists or numbered items
                5. Total of 7 sentences and the entire text should take approximately 45 seconds when narrated (NEVER exceed 50 seconds)
                6. Each sentence should be meaningful and educational, but use exaggerated and dramatic language
                7. Each sentence should be between 12-20 words in length and in English
                8. Include statistics, numbers, and surprising comparisons
                9. The final sentence should end with a shocking fact or thought-provoking question
                10. Don't hesitate to address the viewer in second person (you), as this strengthens connection
                
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
            },
            "de": {
                "system_message": "Sie sind ein Assistent, der kurze, informative Inhalte erstellt.",
                "prompt_template": f"""
                Schreiben Sie einen kurzen, informativen Text über {topic}.
                Dieser Text wird für ein Video von TTS gesprochen werden.
                
                Wichtige Regeln:
                1. Der Text sollte direkt auf den Punkt kommen, keine unnötigen Einleitungen wie "Hallo, heute werde ich über ... sprechen"
                2. Jeder Satz sollte ein eigener Absatz sein, keine Listen oder nummerierten Elemente
                3. Insgesamt 7 Sätze und der gesamte Text sollte beim Vorlesen etwa 45 Sekunden dauern (NIEMALS 50 Sekunden überschreiten)
                4. Jeder Satz sollte aussagekräftig und lehrreich sein
                5. Die Zielgruppe sind allgemeine Zuschauer, verwenden Sie daher keine technische Sprache
                6. Jeder Satz sollte zwischen 12 und 20 Wörter lang und auf Deutsch sein
                7. Der Text sollte nur aus einfachen Sätzen bestehen, insgesamt nur 7 Sätze
                8. Jeder Satz sollte eine Atempause von 2-4 Sekunden enthalten (für Natürlichkeit)
                
                Bitte erstellen Sie einen Text, der die obigen Regeln vollständig einhält, mit insgesamt 7 Sätzen, die 35-45 Sekunden dauern, wenn sie von TTS gelesen werden.
                Geben Sie jeden Satz als eigenen Absatz an.
                """
            },
            "it": {
                "system_message": "Sei un assistente che crea contenuti brevi e informativi.",
                "prompt_template": f"""
                Scrivi un testo breve e informativo su {topic}.
                Questo testo sarà narrato da TTS per un video.
                
                Regole importanti:
                1. Il testo deve andare dritto al punto, senza introduzioni inutili come "ciao, oggi parlerò di..."
                2. Ogni frase deve essere un paragrafo separato, senza elenchi o elementi numerati
                3. Un totale di 7 frasi e l'intero testo dovrebbe richiedere circa 45 secondi quando viene narrato (NON superare MAI i 50 secondi)
                4. Ogni frase deve essere significativa ed educativa
                5. Il pubblico di destinazione è costituito da spettatori generali, quindi usa un linguaggio non tecnico
                6. Ogni frase dovrebbe essere lunga tra le 12 e le 20 parole e in italiano
                7. Il testo dovrebbe consistere solo di frasi semplici, solo 7 frasi in totale
                8. Ogni frase dovrebbe includere una pausa di respirazione di 2-4 secondi (per naturalezza)
                
                Per favore, crea un testo che rispetti pienamente le regole di cui sopra, con un totale di 7 frasi che richiederanno 35-45 secondi quando lette da TTS.
                Fornisci ogni frase come un paragrafo separato.
                """
            },
            "pt": {
                "system_message": "Você é um assistente que cria conteúdo curto e informativo.",
                "prompt_template": f"""
                Escreva um texto curto e informativo sobre {topic}.
                Este texto será narrado por TTS para um vídeo.
                
                Regras importantes:
                1. O texto deve ir direto ao ponto, sem introduções desnecessárias como "olá, hoje vou falar sobre..."
                2. Cada frase deve ser um parágrafo separado, sem listas ou itens numerados
                3. Um total de 7 frases e o texto inteiro deve levar aproximadamente 45 segundos quando narrado (NUNCA exceder 50 segundos)
                4. Cada frase deve ser significativa e educativa
                5. O público-alvo são espectadores gerais, então use linguagem não técnica
                6. Cada frase deve ter entre 12 e 20 palavras de comprimento e em português
                7. O texto deve consistir apenas de frases simples, apenas 7 frases no total
                8. Cada frase deve incluir uma pausa de respiração de 2-4 segundos (para naturalidade)
                
                Por favor, crie um texto que cumpra totalmente as regras acima, com um total de 7 frases que levarão 35-45 segundos quando lidas por TTS.
                Forneça cada frase como um parágrafo separado.
                """
            },
            "ru": {
                "system_message": "Вы помощник, который создает короткий, информативный контент.",
                "prompt_template": f"""
                Напишите короткий, информативный текст о {topic}.
                Этот текст будет озвучен TTS для видео.
                
                Важные правила:
                1. Текст должен быть по существу, без ненужных вступлений типа "привет, сегодня я расскажу о..."
                2. Каждое предложение должно быть отдельным абзацем, без списков или нумерованных элементов
                3. Всего 7 предложений, и весь текст должен занимать примерно 45 секунд при озвучивании (НИКОГДА не превышать 50 секунд)
                4. Каждое предложение должно быть значимым и образовательным
                5. Целевая аудитория - обычные зрители, поэтому используйте нетехнический язык
                6. Каждое предложение должно содержать от 12 до 20 слов и быть на русском языке
                7. Текст должен состоять только из простых предложений, всего 7 предложений
                8. Каждое предложение должно включать паузу для дыхания 2-4 секунды (для естественности)
                
                Пожалуйста, создайте текст, который полностью соответствует приведенным выше правилам, с общим количеством 7 предложений, которые займут 35-45 секунд при чтении TTS.
                Предоставьте каждое предложение как отдельный абзац.
                """
            },
            "zh": {
                "system_message": "您是一位创建简短、信息丰富内容的助手。",
                "prompt_template": f"""
                写一篇关于{topic}的简短、信息丰富的文本。
                此文本将由TTS为视频进行叙述。
                
                重要规则：
                1. 文本应该直接切入主题，没有不必要的介绍，如"你好，今天我将谈论..."
                2. 每个句子应该是单独的段落，没有列表或编号项目
                3. 总共7个句子，整个文本在叙述时应该大约需要45秒（绝不超过50秒）
                4. 每个句子都应该有意义且具有教育性
                5. 目标受众是普通观众，所以使用非技术性语言
                6. 每个句子应该在12-20个词长度之间，并且使用中文
                7. 文本应该只包含简单句子，总共只有7个句子
                8. 每个句子应该包括2-4秒的呼吸停顿（为了自然）
                
                请创建一个完全符合上述规则的文本，总共7个句子，当被TTS阅读时将花费35-45秒。
                提供每个句子作为单独的段落。
                """
            },
            "ja": {
                "system_message": "あなたは短く、情報豊かなコンテンツを作成するアシスタントです。",
                "prompt_template": f"""
                {topic}について短く、情報豊かなテキストを書いてください。
                このテキストはビデオのためにTTSによって朗読されます。
                
                重要なルール：
                1. テキストは要点を直接述べるべきで、「こんにちは、今日は...について話します」などの不必要な導入はしないでください
                2. 各文は別の段落にし、リストや番号付きアイテムは使用しないでください
                3. 合計7文で、テキスト全体が朗読されると約45秒かかるべきです（絶対に50秒を超えないこと）
                4. 各文は意味があり、教育的であるべきです
                5. ターゲットオーディエンスは一般視聴者なので、技術的でない言葉を使用してください
                6. 各文は12〜20語の長さで、日本語であるべきです
                7. テキストは単純な文だけで構成し、合計で7文だけにしてください
                8. 各文は自然さのために2〜4秒の呼吸の一時停止を含めるべきです
                
                TTSで読まれると35〜45秒かかる7文の合計で、上記のルールに完全に準拠するテキストを作成してください。
                各文を別々の段落として提供してください。
                """
            },
            "ko": {
                "system_message": "당신은 짧고 유익한 콘텐츠를 만드는 조수입니다.",
                "prompt_template": f"""
                {topic}에 대한 짧고 유익한 텍스트를 작성하세요.
                이 텍스트는 비디오를 위해 TTS로 나레이션될 것입니다.
                
                중요한 규칙:
                1. 텍스트는 요점을 바로 이야기해야 하며, "안녕하세요, 오늘은 ...에 대해 이야기하겠습니다"와 같은 불필요한 소개가 없어야 합니다
                2. 각 문장은 별도의 단락이어야 하며, 목록이나 번호가 매겨진 항목이 없어야 합니다
                3. 총 7개의 문장이며 전체 텍스트는 나레이션될 때 약 45초가 소요되어야 합니다 (절대 50초를 초과해서는 안 됩니다)
                4. 각 문장은 의미 있고 교육적이어야 합니다
                5. 대상 시청자는 일반 시청자이므로 비기술적인 언어를 사용하세요
                6. 각 문장은 12-20개의 단어 길이이며 한국어여야 합니다
                7. 텍스트는 단순한 문장으로만 구성되어야 하며, 총 7개의 문장만 있어야 합니다
                8. 각 문장은 자연스러움을 위해 2-4초의 호흡 정지를 포함해야 합니다
                
                TTS로 읽힐 때 35-45초가 소요될 총 7개의 문장으로, 위의 규칙을 완전히 준수하는 텍스트를 작성해 주세요.
                각 문장을 별도의 단락으로 제공하세요.
                """
            },
            "ar": {
                "system_message": "أنت مساعد يقوم بإنشاء محتوى قصير ومفيد.",
                "prompt_template": f"""
                اكتب نصًا قصيرًا ومفيدًا عن {topic}.
                سيتم سرد هذا النص بواسطة TTS لفيديو.
                
                قواعد مهمة:
                1. يجب أن يصل النص مباشرة إلى النقطة، بدون مقدمات غير ضرورية مثل "مرحبًا، سأتحدث اليوم عن..."
                2. يجب أن تكون كل جملة فقرة منفصلة، بدون قوائم أو عناصر مرقمة
                3. مجموع 7 جمل ويجب أن يستغرق النص بأكمله حوالي 45 ثانية عند سرده (لا يتجاوز أبدًا 50 ثانية)
                4. يجب أن تكون كل جملة ذات معنى وتعليمية
                5. الجمهور المستهدف هم المشاهدون العامون، لذا استخدم لغة غير تقنية
                6. يجب أن تتراوح كل جملة بين 12-20 كلمة في الطول وباللغة العربية
                7. يجب أن يتكون النص من جمل بسيطة فقط، 7 جمل فقط في المجموع
                8. يجب أن تتضمن كل جملة توقفًا للتنفس من 2-4 ثوانٍ (للطبيعية)
                
                يرجى إنشاء نص يمتثل تمامًا للقواعد المذكورة أعلاه، بمجموع 7 جمل ستستغرق 35-45 ثانية عند قراءتها بواسطة TTS.
                قدم كل جملة كفقرة منفصلة.
                """
            }
        }
        
        # Add default settings for other languages
        default_settings = {
            "system_message": "You are an expert creator of viral content for TikTok and YouTube Shorts. You excel at creating shocking, curiosity-inducing content that hooks viewers instantly.",
            "prompt_template": f"""
            Write a viral, attention-grabbing text about {topic} that will hook viewers instantly.
            This text will be narrated for YouTube Shorts or TikTok.
            
            Critical Rules:
            1. THE FIRST SENTENCE MUST CONTAIN a SHOCKING fact/claim that will SURPRISE viewers or create extreme curiosity
            2. The second sentence should support the shocking first sentence or make it even more interesting
            3. Other sentences should start with phrases like "but what's really shocking is...", "the hidden truth is...", "what's incredible is..."
            4. Each sentence should be a separate paragraph, no lists or numbered items
            5. Total of 7 sentences and the entire text should take approximately 45 seconds when narrated (NEVER exceed 50 seconds)
            6. Each sentence should be meaningful and educational, but use exaggerated and dramatic language
            7. Each sentence should be between 12-20 words in length
            8. Include statistics, numbers, and surprising comparisons
            9. The final sentence should end with a shocking fact or thought-provoking question
            10. Don't hesitate to address the viewer in second person (you), as this strengthens connection
            
            Please create a text in {language} that fully complies with the above rules, with a total of 7 sentences that will take 35-45 seconds when read by TTS.
            Provide each sentence as a separate paragraph.
            """
        }
        
        # Get language settings (or use default if not defined)
        settings = lang_settings.get(language, default_settings)
        
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
        # Return error message
        return {
            "topic": topic,
            "response": [f"Error generating content: {str(e)}"]
        } 