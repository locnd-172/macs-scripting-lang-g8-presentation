import shutil
import tempfile
from pathlib import Path

from insights import analyze, save_insights
from media_tools import download_video, extract_audio, transcribe

DEMO_OUTPUT = Path(__file__).parent / "demo_output"


def naive(post_id, work_root):
    folder = Path(tempfile.mkdtemp(prefix="video-", dir=work_root))
    video = download_video(post_id, folder)
    audio = extract_audio(video)
    if audio is None:
        return "skipped: no audio"  # cleanup below is skipped
    transcript = transcribe(audio)
    shutil.rmtree(folder)

    save_insights(post_id, analyze(transcript))
    return "analyzed"


def managed(post_id, work_root):
    with tempfile.TemporaryDirectory(prefix="video-", dir=work_root) as folder:
        video = download_video(post_id, Path(folder))
        audio = extract_audio(video)
        if audio is None:
            return "skipped: no audio"
        transcript = transcribe(audio)

    save_insights(post_id, analyze(transcript))
    return "analyzed"


def show_case(label, post_id):
    print("-" * 100)
    print(label)
    for name, process in [("naive", naive), ("managed", managed)]:
        folders_before = len(list(DEMO_OUTPUT.iterdir()))
        result = process(post_id, DEMO_OUTPUT)
        leftover = "yes" if len(list(DEMO_OUTPUT.iterdir())) > folders_before else "no"
        print(f"  {name:<8}\tstep: {result:<18}\tleftover files: {leftover}")


def main():
    DEMO_OUTPUT.mkdir(exist_ok=True)
    show_case(label="Successful transcription", post_id="launch")
    show_case(label="No audio track (early return)", post_id="silent")


if __name__ == "__main__":
    main()
