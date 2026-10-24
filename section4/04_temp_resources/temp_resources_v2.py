"""Application 4 (v2) - Temporary resources in a video analytics job.

A social media analytics job turns posts into insights:

    download video (mp4) -> extract audio (wav) -> transcribe -> analyze with an LLM -> save

The video and audio are large, are needed only until the transcript exists, and must be
gone however the job ends. Files left behind by failed jobs eventually fill the disk.
The tools work on paths, so the scratch space is a folder. All the tools are fake.

  pipeline_naive.py    makes a folder with mkdtemp() and deletes it at the end
  pipeline_managed.py  uses TemporaryDirectory(), around only the steps that need the files
"""

import tempfile
from contextlib import suppress
from pathlib import Path

import pipeline_managed
import pipeline_naive
from media_tools import ToolError, download_video, extract_audio

# (what happens, post id). The fake tools fail depending on the id.
POSTS = [
    ("success", "ok"),
    ("download fails", "broken-link"),
    ("audio extraction fails", "corrupt-video"),
    ("no audio track", "silent"),
    ("transcription fails", "model-crash"),
    ("LLM call fails", "llm-timeout"),
    ("database save fails", "db-down"),
]


def describe(folder):
    files = sorted(Path(folder).iterdir())
    return ", ".join(f"{f.name} ({f.stat().st_size // 1024} KiB)" for f in files)


def show_lifecycle():
    print("Lifecycle of one run")
    with tempfile.TemporaryDirectory(prefix="transcribe-") as folder:
        video = download_video("ok", Path(folder))
        extract_audio(video)
        print("  inside the block:", describe(folder))
    print("  after the block : folder exists?", Path(folder).exists())


def left_behind(process_post, post_id):
    """Run one post in an empty work folder and report what is still there afterwards."""
    with tempfile.TemporaryDirectory() as work_root:
        with suppress(ToolError):
            process_post(post_id, Path(work_root))
        files = [f for f in Path(work_root).rglob("*") if f.is_file()]
        folders = [f for f in Path(work_root).iterdir()]
        kib = sum(f.stat().st_size for f in files) // 1024
    return f"{len(folders)} / {kib} KiB"


def show_left_behind():
    print("Left behind after each kind of run (folders / size)")
    print(f"  {'':<24}{'naive':<20}{'context manager'}")
    for what_happens, post_id in POSTS:
        naive = left_behind(pipeline_naive.process_post, post_id)
        managed = left_behind(pipeline_managed.process_post, post_id)
        print(f"  {what_happens:<24}{naive:<20}{managed}")


def main():
    show_lifecycle()
    print()
    show_left_behind()


if __name__ == "__main__":
    main()
