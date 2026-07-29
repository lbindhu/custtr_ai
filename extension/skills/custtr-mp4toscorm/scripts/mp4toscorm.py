#!/usr/bin/env python3
"""
mp4toscorm.py - Convert MP4 video to SCORM 1.2 package
No external dependencies required. Uses only Python standard library.
"""

import argparse
import os
import shutil
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path


def get_video_duration_windows(video_path):
    """Get video duration in seconds using PowerShell (no ffmpeg needed)."""
    ps_script = f"""
    Add-Type -AssemblyName PresentationCore
    $mediaPlayer = New-Object System.Windows.Media.MediaPlayer
    $uri = New-Object System.Uri('{str(video_path).replace(chr(92), "/")}')
    $mediaPlayer.Open($uri)
    Start-Sleep -Seconds 3
    $dur = $mediaPlayer.NaturalDuration
    if ($dur.HasTimeSpan) {{ $dur.TimeSpan.TotalSeconds }} else {{ 0 }}
    $mediaPlayer.Close()
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True, text=True, timeout=15
        )
        return float(result.stdout.strip())
    except Exception:
        return 0


def get_video_duration_mp4box(video_path):
    """Fallback: parse MP4 moov/mvhd atom to get duration (pure Python)."""
    try:
        with open(video_path, "rb") as f:
            data = f.read()
        # Search for 'mvhd' atom
        idx = data.find(b"mvhd")
        if idx == -1:
            return 0
        version = data[idx + 4]
        if version == 1:
            # 64-bit mvhd
            timescale = struct.unpack(">I", data[idx + 20:idx + 24])[0]
            duration = struct.unpack(">Q", data[idx + 24:idx + 32])[0]
        else:
            # 32-bit mvhd
            timescale = struct.unpack(">I", data[idx + 12:idx + 16])[0]
            duration = struct.unpack(">I", data[idx + 16:idx + 20])[0]
        if timescale == 0:
            return 0
        return duration / timescale
    except Exception:
        return 0


def get_video_duration(video_path):
    """Try PowerShell first (Windows), fall back to MP4 atom parsing."""
    duration = get_video_duration_windows(video_path)
    if duration <= 0:
        duration = get_video_duration_mp4box(video_path)
    return duration


def generate_manifest(title, video_filename):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="course_manifest" version="1.1"
  xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
  xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd
                       http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>1.2</schemaversion>
  </metadata>
  <organizations default="course_org">
    <organization identifier="course_org">
      <title>{title}</title>
      <item identifier="item_1" identifierref="resource_1">
        <title>{title}</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="resource_1" type="webcontent" adlcp:scormtype="sco" href="index.html">
      <file href="index.html"/>
      <file href="{video_filename}"/>
    </resource>
  </resources>
</manifest>"""


def generate_html(title, video_filename, duration, threshold):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{
      width: 100%;
      height: 100%;
    }}
    body {{
      background: #282828;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-start;
      min-height: 100vh;
      font-family: Arial, sans-serif;
      color: #fff;
    }}
    h1 {{
      font-size: 1.2rem;
      margin: 12px 0 8px 0;
      color: #eee;
      text-align: center;
      padding: 0 16px;
    }}
    video {{
      width: 100%;
      max-width: 1280px;
      height: auto;
      display: block;
      background: #000;
      outline: none;
      margin: 0 auto;
    }}
    #status {{
      margin-top: 8px;
      font-size: 0.9rem;
      color: #aaa;
    }}
    #complete-badge {{
      display: none;
      margin-top: 8px;
      background: #4caf50;
      color: #fff;
      padding: 6px 18px;
      border-radius: 4px;
      font-size: 0.95rem;
    }}
    #player-wrapper {{
      position: relative;
      width: 100%;
      max-width: 1280px;
    }}
    #exit-btn {{
      position: absolute;
      top: -26px;
      right: 0;
      background: none;
      color: #aaa;
      border: none;
      font-size: 1.1rem;
      cursor: pointer;
      padding: 0;
      line-height: 1;
    }}
    #exit-btn:hover {{
      color: #fff;
    }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div id="player-wrapper">
    <button id="exit-btn" onclick="exitCourse()" title="Exit Course">&#x2715;</button>
    <video id="courseVideo" controls>
      <source src="{video_filename}" type="video/mp4">
      Your browser does not support the video tag.
    </video>
  </div>
  <div id="complete-badge">&#10003; Course Completed</div>

  <script>
    var API = null;
    var completed = false;
    var threshold = {threshold};
    var totalDuration = {duration};

    function findAPI(win) {{
      var tries = 0;
      while (win.API == null && win.parent != null && win.parent != win) {{
        tries++;
        if (tries > 7) return null;
        win = win.parent;
      }}
      return win.API;
    }}

    function getAPI() {{
      var api = findAPI(window);
      if (api == null && window.opener != null) api = findAPI(window.opener);
      return api;
    }}

    function initSCORM() {{
      API = getAPI();
      if (!API) {{ console.warn("SCORM API not found — running in standalone mode."); return; }}
      API.LMSInitialize("");
      var savedTime = API.LMSGetValue("cmi.core.lesson_location");
      if (savedTime && parseFloat(savedTime) > 0) {{
        document.getElementById("courseVideo").currentTime = parseFloat(savedTime);
      }}
      var status = API.LMSGetValue("cmi.core.lesson_status");
      if (status === "passed" || status === "completed") {{
        completed = true;
        showComplete();
      }} else {{
        API.LMSSetValue("cmi.core.lesson_status", "incomplete");
        API.LMSCommit("");
      }}
    }}

    function showComplete() {{
      document.getElementById("complete-badge").style.display = "inline-block";
    }}

    function updateProgress(percent, currentTime) {{
      if (!API) return;
      API.LMSSetValue("cmi.core.lesson_location", currentTime.toFixed(2));
      API.LMSSetValue("cmi.core.score.raw", percent.toFixed(0));
      API.LMSSetValue("cmi.core.score.min", "0");
      API.LMSSetValue("cmi.core.score.max", "100");
      if (!completed && percent >= threshold) {{
        completed = true;
        API.LMSSetValue("cmi.core.lesson_status", "passed");
        showComplete();
      }}
      API.LMSCommit("");
    }}

    function finishSCORM() {{
      if (!API) return;
      API.LMSFinish("");
    }}

    function exitCourse() {{
      var video = document.getElementById("courseVideo");
      video.pause();
      finishSCORM();
      window.close();
    }}

    var video = document.getElementById("courseVideo");

    video.addEventListener("timeupdate", function () {{
      if (totalDuration <= 0) return;
      var percent = (video.currentTime / totalDuration) * 100;
      if (API) updateProgress(percent, video.currentTime);
    }});

    window.addEventListener("beforeunload", finishSCORM);
    initSCORM();
  </script>
</body>
</html>"""


MAX_SIZE_MB = 90


def compress_video_windows(input_path, output_path):
    """Compress video using PowerShell Windows.Media.Transcoding (no ffmpeg needed)."""
    ps_script = f"""
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    [void][Windows.Media.Transcoding.MediaTranscoder, Windows.Media, ContentType=WindowsRuntime]
    $transcoder = New-Object Windows.Media.Transcoding.MediaTranscoder
    $profile = [Windows.Media.MediaProperties.MediaEncodingProfile]::CreateMp4(
        [Windows.Media.MediaProperties.VideoEncodingQuality]::Vga
    )
    $inputFile = [Windows.Storage.StorageFile]::GetFileFromPathAsync('{str(input_path).replace(chr(92), "\\\\")}').GetAwaiter().GetResult()
    $outputFile = [Windows.Storage.StorageFile]::GetFileFromPathAsync('{str(output_path).replace(chr(92), "\\\\")}').GetAwaiter().GetResult()
    $result = $transcoder.PrepareFileTranscodeAsync($inputFile, $outputFile, $profile).GetAwaiter().GetResult()
    if ($result.CanTranscode) {{
        $result.TranscodeAsync().GetAwaiter().GetResult()
        Write-Output "OK"
    }} else {{
        Write-Output "FAIL:$($result.FailureReason)"
    }}
    """
    try:
        result = subprocess.run(
            [r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe", "-Command", ps_script],
            capture_output=True, text=True, timeout=300
        )
        output = result.stdout.strip()
        return "OK" in output
    except Exception as e:
        print(f"  Transcoding error: {e}")
        return False


FFMPEG_FALLBACK_PATH = r"C:\Users\mutyalaa\ffmpeg\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
FFPROBE_FALLBACK_PATH = r"C:\Users\mutyalaa\ffmpeg\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"


def _find_exe(name, fallback):
    """Find executable on PATH or use fallback path."""
    import shutil as _shutil
    found = _shutil.which(name)
    if found:
        return found
    if Path(fallback).exists():
        return fallback
    return None


def compress_video_ffmpeg(input_path, output_path, target_mb=80):
    """Compress video using ffmpeg. Uses 2-pass encoding to reliably hit target size."""
    ffmpeg = _find_exe("ffmpeg", FFMPEG_FALLBACK_PATH)
    ffprobe = _find_exe("ffprobe", FFPROBE_FALLBACK_PATH)
    if not ffmpeg or not ffprobe:
        return False
    try:
        # Get duration for bitrate calculation
        probe = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(input_path)],
            capture_output=True, text=True, timeout=30
        )
        duration = float(probe.stdout.strip())
        if duration <= 0:
            return False
        # target bitrate in kbps (leave 96k for audio)
        audio_kbps = 96
        target_kbps = int((target_mb * 8 * 1024) / duration) - audio_kbps
        target_kbps = max(100, target_kbps)

        # Pass 1
        pass1 = subprocess.run(
            [ffmpeg, "-y", "-i", str(input_path),
             "-vcodec", "libx264", "-b:v", f"{target_kbps}k",
             "-preset", "slow", "-pass", "1",
             "-an", "-f", "null", "NUL"],
            capture_output=True, text=True, timeout=600
        )
        # Pass 2
        result = subprocess.run(
            [ffmpeg, "-y", "-i", str(input_path),
             "-vcodec", "libx264", "-b:v", f"{target_kbps}k",
             "-preset", "slow", "-pass", "2",
             "-acodec", "aac", "-b:a", f"{audio_kbps}k",
             str(output_path)],
            capture_output=True, text=True, timeout=600
        )
        return result.returncode == 0 and Path(output_path).exists() and Path(output_path).stat().st_size > 0
    except Exception:
        return False


def reduce_video_size(video_path, tmpdir):
    """
    If video is >90MB, compress it. Returns path to the video to use
    (either original or compressed copy in tmpdir).
    """
    size_mb = video_path.stat().st_size / (1024 * 1024)
    if size_mb <= MAX_SIZE_MB:
        return video_path

    print(f"  Video is {size_mb:.1f} MB — exceeds {MAX_SIZE_MB} MB limit. Compressing...")
    compressed_path = tmpdir / ("compressed_" + video_path.name)

    # Create an empty file first (required by Windows.Media.Transcoding)
    compressed_path.touch()

    # Try ffmpeg first (better quality control), then PowerShell transcoding
    success = compress_video_ffmpeg(video_path, compressed_path)
    if not success:
        print("  ffmpeg not found or failed — trying Windows built-in transcoding...")
        success = compress_video_windows(video_path, compressed_path)

    if success and compressed_path.exists() and compressed_path.stat().st_size > 0:
        new_mb = compressed_path.stat().st_size / (1024 * 1024)
        print(f"  Compressed to {new_mb:.1f} MB")
        if new_mb > MAX_SIZE_MB:
            print(f"  Warning: compressed file is still {new_mb:.1f} MB (>{MAX_SIZE_MB} MB). Video may be too long to compress further without severe quality loss.")
        return compressed_path
    else:
        print("  Warning: compression failed. Using original file. LMS may reject if too large.")
        return video_path


def create_scorm_package(video_path, title, output_dir, threshold=80):
    video_path = Path(video_path).resolve()
    output_dir = Path(output_dir).resolve()
    video_filename = video_path.name

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    print(f"Video  : {video_path}")
    print(f"Title  : {title}")
    print(f"Output : {output_dir}")

    size_mb = video_path.stat().st_size / (1024 * 1024)
    print(f"File size: {size_mb:.1f} MB")

    print(f"Getting video duration...")
    duration = get_video_duration(video_path)
    print(f"Duration: {duration:.1f} seconds")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Compress if needed before packaging
        source_video = reduce_video_size(video_path, tmpdir)

        print("Copying video file...")
        dest = tmpdir / video_filename
        if source_video != dest:
            shutil.copy2(source_video, dest)

        manifest = generate_manifest(title, video_filename)
        html = generate_html(title, video_filename, duration, threshold)

        (tmpdir / "imsmanifest.xml").write_text(manifest, encoding="utf-8")
        (tmpdir / "index.html").write_text(html, encoding="utf-8")

        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title).strip()
        zip_name = f"{safe_title}.zip"
        zip_path = output_dir / zip_name

        print("Creating SCORM ZIP package...")
        scorm_files = {"imsmanifest.xml", "index.html", video_filename}
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in tmpdir.iterdir():
                if file.name in scorm_files:
                    zf.write(file, file.name)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\nDone!")
    print(f"  ZIP path : {zip_path}")
    print(f"  Size     : {size_mb:.2f} MB")
    print(f"\nUpload this ZIP to your LMS as a SCORM 1.2 package.")
    return zip_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert MP4 to SCORM 1.2 package (no authoring tool required)")
    parser.add_argument("--video", required=True, help="Full path to MP4 video file")
    parser.add_argument("--title", required=True, help="Course title")
    parser.add_argument("--output", required=True, help="Output directory for the ZIP")
    parser.add_argument("--threshold", type=float, default=80, help="Completion % threshold (default: 80)")
    args = parser.parse_args()

    create_scorm_package(args.video, args.title, args.output, args.threshold)
