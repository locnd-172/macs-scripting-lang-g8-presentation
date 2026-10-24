"""Fake versions of the tools that work on files: a downloader, ffmpeg and a speech model.

They write real files of a realistic size and fail for certain post ids, so the demo can
show each way a job can go wrong. Nothing here touches the network.
"""

KB = 1024


class ToolError(Exception):
    pass


def download_video(post_id, folder):
    video = folder / f"{post_id}.mp4"
    if post_id == "broken-link":
        video.write_bytes(bytes(256 * KB))  # the connection drops halfway
        raise ToolError("download interrupted")
    video.write_bytes(bytes(1024 * KB))
    return video


def extract_audio(video):
    """Returns the audio file, or None when the video has no audio track."""
    if video.stem == "corrupt-video":
        raise ToolError("ffmpeg: invalid data found")
    if video.stem == "silent":
        return None
    audio = video.with_suffix(".wav")
    audio.write_bytes(bytes(256 * KB))
    return audio


def transcribe(audio):
    if audio.stem == "model-crash":
        raise ToolError("speech model ran out of memory")
    return "Welcome back. Today we are launching our new product."
