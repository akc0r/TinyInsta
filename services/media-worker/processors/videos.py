"""Video processing — poster thumbnail + 720p transcode (ffmpeg)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import storage


def _ffmpeg(*args: str) -> None:
    # capture_output keeps ffmpeg's noisy stderr out of the logs unless it fails,
    # in which case it travels with the CalledProcessError for debugging.
    subprocess.run(["ffmpeg", "-y", *args], check=True, capture_output=True)


def process(original_url: str) -> dict[str, str]:
    object_key = storage.key_from_url(original_url)
    raw = storage.download(object_key)

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "source"
        thumb = Path(tmp) / "thumb.jpg"
        out = Path(tmp) / "720p.mp4"
        src.write_bytes(raw)

        # Representative frame for the poster image.
        _ffmpeg(
            "-i", str(src),
            "-vf", "thumbnail,scale=320:-2",
            "-frames:v", "1",
            str(thumb),
        )
        # H.264/AAC, capped at 720p height (never upscaled), faststart for
        # progressive web playback.
        _ffmpeg(
            "-i", str(src),
            "-vf", "scale=-2:'min(720,ih)'",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(out),
        )

        return {
            "thumb": storage.upload(
                f"{object_key}/thumb.jpg", thumb.read_bytes(), "image/jpeg"
            ),
            "720p": storage.upload(
                f"{object_key}/720p.mp4", out.read_bytes(), "video/mp4"
            ),
        }
