#!/usr/bin/env python3
"""Generate the voice lines for render_battle_story.py with Microsoft Edge neural TTS.

Rohan: en-IN-PrabhatNeural, Meera: en-IN-NeerjaExpressiveNeural. Writes one WAV per
line to audio/battle-story/ (44.1 kHz mono) and prints each line's length. Needs
`pip install edge-tts` and network access. The CA bundle in SSL_CERT_FILE is used
when set (edge-tts otherwise only trusts certifi).

Usage: python3 make_battle_story_voices.py
"""
import asyncio
import os
import ssl
import subprocess

import edge_tts
import edge_tts.communicate as communicate

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "audio", "battle-story")
VOICE = {"rohan": "en-IN-PrabhatNeural", "meera": "en-IN-NeerjaExpressiveNeural"}

# (id, speaker, spoken text, rate, pitch)
LINES = [
    ("01", "rohan", "I'm basically the Sudoku king. Nobody beats me.", "+12%", "+0Hz"),
    ("02", "meera", "Oh really? Ever tried Battle Mode in Sudoku Original?", "+12%", "+0Hz"),
    ("03", "rohan", "Battle Mode?", "+5%", "+0Hz"),
    ("04", "meera", "Same puzzle. Same clock. Loser buys chai!", "+12%", "+0Hz"),
    ("05", "rohan", "Deal. Easy chai.", "+10%", "+0Hz"),
    ("06", "meera", "Room code B 7 K 4 P 9. Join!", "+15%", "+0Hz"),
    ("07", "rohan", "In. Let's go!", "+10%", "+0Hz"),
    ("08", "rohan", "Already sixty percent! Too easy.", "+15%", "+0Hz"),
    ("09", "meera", "Mm-hmm.", "+0%", "+0Hz"),
    ("10", "rohan", "Wait. How are you at ninety percent?!", "+20%", "+15Hz"),
    ("11", "meera", "Chai's on you, King.", "+5%", "+0Hz"),
    ("12", "rohan", "Rematch. Now.", "+10%", "+0Hz"),
    ("13", "meera", "Download it on the Play Store.", "+10%", "+0Hz"),
    ("14", "rohan", "It's free!", "+10%", "+0Hz"),
]


async def main():
    cafile = os.environ.get("SSL_CERT_FILE")
    if cafile:
        communicate._SSL_CTX = ssl.create_default_context(cafile=cafile)
    os.makedirs(OUT, exist_ok=True)
    for lid, who, text, rate, pitch in LINES:
        mp3 = os.path.join(OUT, f"{lid}-{who}.mp3")
        wav = mp3[:-4] + ".wav"
        await edge_tts.Communicate(text, VOICE[who], rate=rate, pitch=pitch,
                                   proxy=os.environ.get("HTTPS_PROXY")).save(mp3)
        # trim leading/trailing silence, convert to 44.1 kHz mono
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-af",
                        "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                        "silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                        "-ar", "44100", "-ac", "1", wav], check=True)
        os.remove(mp3)
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                             "-of", "csv=p=0", wav]))
        print(f"{lid} {who:5s} {dur:5.2f}s  {text}")


if __name__ == "__main__":
    asyncio.run(main())
