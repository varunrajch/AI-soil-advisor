"""Text to speech for the Action Card (gTTS, mp3)."""
import io
import logging
import time

from .logging_setup import log

logger = logging.getLogger("nela.tts")


def synthesize(text: str, lang: str) -> bytes:
    from gtts import gTTS

    start = time.perf_counter()
    buf = io.BytesIO()
    gTTS(text, lang=lang).write_to_fp(buf)
    log(logger, logging.INFO, "tts.done", lang=lang, chars=len(text), bytes=buf.tell(),
        ms=round((time.perf_counter() - start) * 1000))
    return buf.getvalue()
