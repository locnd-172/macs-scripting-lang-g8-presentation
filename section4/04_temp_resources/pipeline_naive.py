"""The pipeline as it is usually first written: make a folder, do the work, delete the folder."""

import shutil
import tempfile
from pathlib import Path

from insights import analyze, save_insights
from media_tools import download_video, extract_audio, transcribe


def process_post(post_id, work_root):
    folder = Path(tempfile.mkdtemp(prefix="transcribe-", dir=work_root))

    video = download_video(post_id, folder)
    audio = extract_audio(video)
    if audio is None:
        return "skipped, no audio track"  # the cleanup at the bottom never runs

    transcript = transcribe(audio)
    insights = analyze(post_id, transcript)
    save_insights(post_id, insights)

    shutil.rmtree(folder)  # only reached if every step above worked
    return "analyzed"
