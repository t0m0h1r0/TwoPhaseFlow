#!/usr/bin/env python3
"""Create a time-ordered movie from a one-page PDF frame sequence.

Typical usage for the Chapter 14 capillary velocity snapshots:

  .venv/bin/python3 scripts/pdf_sequence_movie.py \
      experiment/ch14/results/ch14_capillary \
      --glob 'velocity_t*.pdf' \
      --output experiment/ch14/results/ch14_capillary/velocity_movie.mp4 \
      --fps 20 \
      --dpi 160 \
      --force

Frames are sorted by the numeric ``t`` token in names such as
``velocity_t24.401.pdf``.  Rendering is delegated to ``pdftoppm`` and MP4
encoding is delegated to either ``ffmpeg`` on PATH or the optional
``imageio-ffmpeg`` package.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence


TIME_TOKEN = re.compile(r"(?:^|_)t(?P<time>[+-]?\d+(?:\.\d+)?)")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Build an MP4 movie from a time-ordered PDF frame sequence.",
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing one-page PDF frames.",
    )
    parser.add_argument(
        "--glob",
        default="velocity_t*.pdf",
        help="Frame filename glob relative to input_dir.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output movie path. Defaults to <input_dir>/velocity_movie.mp4.",
    )
    parser.add_argument("--fps", type=float, default=20.0, help="Movie frame rate.")
    parser.add_argument("--dpi", type=int, default=160, help="PDF rasterization DPI.")
    parser.add_argument(
        "--limit",
        type=int,
        help="Use only the first N sorted frames; useful for smoke tests.",
    )
    parser.add_argument(
        "--keep-frames",
        action="store_true",
        help="Keep the temporary PNG frame directory after encoding.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing output movie.",
    )
    return parser.parse_args(argv)


def frame_sort_key(path: Path) -> tuple[int, float | str, str]:
    """Return a stable numeric-time sort key for a PDF frame path."""
    match = TIME_TOKEN.search(path.stem)
    if match:
        return (0, float(match.group("time")), path.name)
    return (1, path.name, path.name)


def discover_frames(input_dir: Path, pattern: str, limit: int | None) -> list[Path]:
    """Find and sort PDF frames under ``input_dir``."""
    frames = sorted(input_dir.glob(pattern), key=frame_sort_key)
    if limit is not None:
        frames = frames[:limit]
    if not frames:
        raise SystemExit(f"no frames matched {input_dir / pattern}")
    return frames


def find_ffmpeg() -> str:
    """Find an ffmpeg executable from PATH or optional imageio-ffmpeg."""
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise SystemExit(
            "MP4 encoding needs ffmpeg. Install one of:\n"
            "  brew install ffmpeg\n"
            "  .venv/bin/python3 -m pip install imageio-ffmpeg"
        ) from exc
    return imageio_ffmpeg.get_ffmpeg_exe()


def require_tool(name: str) -> str:
    """Return a required executable path or exit with a clear message."""
    executable = shutil.which(name)
    if not executable:
        raise SystemExit(f"required executable not found on PATH: {name}")
    return executable


def run_command(cmd: Sequence[str]) -> None:
    """Run a subprocess and surface a compact failure message."""
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        return
    stderr_tail = "\n".join(result.stderr.splitlines()[-5:])
    raise SystemExit(
        f"command failed ({result.returncode}): {' '.join(cmd)}\n{stderr_tail}"
    )


def render_pdf_frames(frames: Sequence[Path], frame_dir: Path, dpi: int) -> None:
    """Rasterize one-page PDF frames to numbered PNG files."""
    pdftoppm = require_tool("pdftoppm")
    total = len(frames)
    for index, pdf_path in enumerate(frames, start=1):
        output_prefix = frame_dir / f"frame_{index:06d}"
        run_command(
            [
                pdftoppm,
                "-png",
                "-singlefile",
                "-r",
                str(dpi),
                str(pdf_path),
                str(output_prefix),
            ]
        )
        if index == 1 or index == total or index % 50 == 0:
            print(f"rendered {index}/{total}: {pdf_path.name}", flush=True)


def encode_mp4(frame_dir: Path, output: Path, fps: float, force: bool) -> None:
    """Encode numbered PNG frames as an H.264 MP4 movie."""
    ffmpeg = find_ffmpeg()
    output.parent.mkdir(parents=True, exist_ok=True)
    overwrite = "-y" if force else "-n"
    run_command(
        [
            ffmpeg,
            overwrite,
            "-framerate",
            f"{fps:g}",
            "-start_number",
            "1",
            "-i",
            str(frame_dir / "frame_%06d.png"),
            "-vf",
            "pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    input_dir = args.input_dir.resolve()
    output = (
        args.output.resolve()
        if args.output is not None
        else input_dir / "velocity_movie.mp4"
    )
    if output.exists() and not args.force:
        raise SystemExit(f"output exists; pass --force to overwrite: {output}")

    frames = discover_frames(input_dir, args.glob, args.limit)
    print(
        f"frames: {len(frames)} "
        f"({frames[0].name} -> {frames[-1].name}), fps={args.fps:g}, dpi={args.dpi}",
        flush=True,
    )

    if args.keep_frames:
        frame_dir = output.with_suffix("")
        frame_dir.mkdir(parents=True, exist_ok=True)
        render_pdf_frames(frames, frame_dir, args.dpi)
        encode_mp4(frame_dir, output, args.fps, args.force)
        print(f"kept frames: {frame_dir}", flush=True)
    else:
        with tempfile.TemporaryDirectory(prefix="pdfseq_movie_") as tmp:
            frame_dir = Path(tmp)
            render_pdf_frames(frames, frame_dir, args.dpi)
            encode_mp4(frame_dir, output, args.fps, args.force)

    print(f"wrote: {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
