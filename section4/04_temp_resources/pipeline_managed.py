"""The same pipeline with a temporary folder that is deleted whatever happens."""

import tempfile
from pathlib import Path

from insights import analyze, save_insights
from media_tools import download_video, extract_audio, transcribe


def get_transcript(post_id, work_root):
    """The video and audio only exist inside this block."""
    with tempfile.TemporaryDirectory(prefix="transcribe-", dir=work_root) as folder:
        video = download_video(post_id, Path(folder))
        audio = extract_audio(video)
        if audio is None:
            return None
        return transcribe(audio)


def process_post(post_id, work_root):
    transcript = get_transcript(post_id, work_root)
    if transcript is None:
        return "skipped, no audio track"

    # The video and audio are already gone, so the slow LLM call does not hold them
    insights = analyze(post_id, transcript)
    save_insights(post_id, insights)
    return "analyzed"
