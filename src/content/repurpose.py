"""
Content repurposing: transcript → Turkish TikTok/Reels script
Uses GPT-4o-mini to adapt (not translate) content for Turkish audience.
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """Sen deneyimli bir Türk sosyal medya içerik üreticisisin.
TikTok ve Instagram Reels için viral içerikler üretiyorsun.
Verilen transkripti Türk izleyici için adapte etmek senin işin.

TEMEL KURAL: Çeviri yapma — adapte et.
İçeriğin özünü koru ama Türk TikTok kültürüne, diline ve tonuna uyarla."""

REPURPOSE_PROMPT = """Aşağıdaki TikTok/Reels videosunun transkriptini analiz et ve Türk izleyici için adapte et.

TRANSKRIPT:
{transcript}

---

Şu adımları izle:

1. İÇERİK TİPİ: Bu video ne tür? (tutorial / ipuçları / hikaye / motivasyon / eğlence / bilgi / diğer)

2. ANA MESAJ: Videonun tek cümlelik özü nedir?

3. HOOK YAZIMI:
   - İlk 2-3 saniyede izleyiciyi durduracak Türkçe hook yaz
   - Format seç: soru / şok ifadesi / merak / rakam/istatistik / "Bunu bilmiyorsan..."
   - Hook neden bu formatta olmalı? Kısa gerekçe ver.

4. TÜRKÇE SCRIPT:
   - Hook'la başla, akıcı şekilde devam et
   - Kısa cümleler, konuşma dili, TikTok ritmi
   - İçeriği değiştirme — Türk izleyici için adapte et
   - Sonunda net bir CTA (çağrı) ekle

5. 3 DESCRIPTION SEÇENEĞİ:
   - Samimi ton: arkadaşça, sıradan dil
   - Merak uyandıran: soru/gizem içerikli
   - Direkt/Güçlü: net, iddialı

Her description: max 150 karakter + 3-5 alakalı Türkçe hashtag

---

SADECE JSON döndür, başka hiçbir şey yazma:

{{
  "content_type": "...",
  "core_message": "...",
  "hook": {{
    "text": "...",
    "format": "soru/şok/merak/rakam/diğer",
    "reasoning": "..."
  }},
  "script": "...",
  "descriptions": [
    {{"text": "...", "tone": "samimi", "hashtags": ["...", "..."]}},
    {{"text": "...", "tone": "merak_uyandiran", "hashtags": ["...", "..."]}},
    {{"text": "...", "tone": "direkt_guclu", "hashtags": ["...", "..."]}}
  ]
}}"""


def repurpose_for_turkish(transcript: str) -> dict:
    """
    Adapt a TikTok transcript for Turkish audience using Gemini.

    Returns dict with: content_type, core_message, hook, script, descriptions
    """
    if not os.getenv('GEMINI_API_KEY'):
        raise Exception(
            "Script oluşturmak için GEMINI_API_KEY gerekli.\n"
            ".env dosyasına ekle."
        )

    from google import genai
    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    full_prompt = SYSTEM_PROMPT + '\n\n' + REPURPOSE_PROMPT.format(transcript=transcript.strip())
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=full_prompt,
    )
    raw = response.text.strip()

    # Strip markdown code block if present
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)
