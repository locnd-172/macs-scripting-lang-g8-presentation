def download_video(post_id, folder):
    video = folder / f"{post_id}.mp4"
    video.write_bytes(b"video data")
    return video


def extract_audio(video):
    # check the video name to simulate a video with no audio track
    if video.stem == "silent":
        return None
    audio = video.with_suffix(".wav")
    audio.write_bytes(b"audio data")
    return audio


def transcribe(audio):
    return "Transcript of the video."
