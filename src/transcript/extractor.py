"""
Video transcript extraction
Downloads video from Apify CDN URL (no bot detection), transcribes via Gemini.
"""

import os
import time
import tempfile
import requests


def extract_transcript(video_url: str, download_url: str = '') -> str:
    """
    Download TikTok video and return transcript.

    Args:
        video_url:    TikTok web URL (https://www.tiktok.com/@user/video/...)
        download_url: Direct CDN URL from Apify (preferred — bypasses bot detection)

    Returns:
        Transcript text string
    """
    if not (os.getenv('GEMINI_API_KEY') or os.getenv('OPENAI_API_KEY')):
        raise Exception(
            "Transcript extraction requires an API key.\n"
            "Set GEMINI_API_KEY (free tier) or OPENAI_API_KEY in .env"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, 'video.mp4')

        if download_url:
            # Fast path: direct CDN download (no bot detection)
            print("  📥 Downloading via Apify CDN URL...")
            _download_direct(download_url, video_path)
        else:
            # Fallback: yt-dlp (may fail on TikTok due to bot detection)
            print("  📥 Downloading via yt-dlp (fallback)...")
            video_path = _download_yt_dlp(video_url, tmpdir)

        if os.getenv('GEMINI_API_KEY'):
            print("  🎙️ Transcribing with Gemini...")
            return _transcribe_gemini(video_path)

        print("  🎙️ Transcribing with Whisper...")
        return _transcribe_whisper(video_path)


def _download_direct(url: str, output_path: str) -> None:
    """Download video from CDN URL directly using requests."""
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Referer': 'https://www.tiktok.com/',
    }
    resp = requests.get(url, headers=headers, stream=True, timeout=60)
    resp.raise_for_status()

    with open(output_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    size_mb = os.path.getsize(output_path) / 1_048_576
    print(f"  ✓ Downloaded ({size_mb:.1f} MB)")


def _download_yt_dlp(url: str, output_dir: str) -> str:
    """Fallback: download via yt-dlp. Returns file path."""
    try:
        import yt_dlp
    except ImportError:
        raise Exception("yt-dlp is not installed. Run: pip install yt-dlp")

    ydl_opts = {
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'format': 'mp4/bestvideo+bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)


def _transcribe_gemini(video_path: str) -> str:
    """Transcribe using Gemini 2.0 Flash (supports video natively)."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

    print("  📤 Uploading to Gemini Files API...")
    video_file = client.files.upload(
        file=video_path,
        config=types.UploadFileConfig(
            display_name='tiktok_video.mp4',
            mime_type='video/mp4',
        ),
    )

    # Wait for file to become ACTIVE (processing can take a few seconds)
    print("  ⏳ Waiting for file to be processed...")
    for _ in range(30):
        video_file = client.files.get(name=video_file.name)
        if video_file.state.name == 'ACTIVE':
            break
        if video_file.state.name == 'FAILED':
            raise Exception("Gemini file processing failed")
        time.sleep(2)
    else:
        raise Exception("Gemini file processing timed out (60s)")

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[
            types.Part.from_uri(
                file_uri=video_file.uri,
                mime_type='video/mp4',
            ),
            types.Part(
                text=(
                    "Transcribe all speech in this video accurately. "
                    "Return ONLY the spoken words — no timestamps, no descriptions, no labels. "
                    "If there is no speech, return '[Konuşma yok / No speech detected]'."
                )
            ),
        ],
    )

    # Clean up uploaded file
    try:
        client.files.delete(name=video_file.name)
    except Exception:
        pass

    return response.text.strip()


def _transcribe_whisper(video_path: str) -> str:
    """Transcribe using OpenAI Whisper API ($0.006/min)."""
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

    with open(video_path, 'rb') as f:
        result = client.audio.transcriptions.create(
            model='whisper-1',
            file=f,
            response_format='text',
        )

    return result.strip()
