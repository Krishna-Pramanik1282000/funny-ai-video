import os
import subprocess
import textwrap
from PIL import Image, ImageDraw, ImageFont

WIDTH = 1080
HEIGHT = 1920
FPS = 30

STORY_FILE = "/github/workspace/input/story.txt"
OUTPUT_DIR = "/github/workspace/output"
FRAMES_DIR = "/tmp/funny_frames"
VIDEO_FILE = os.path.join(OUTPUT_DIR, "funny_video.mp4")
AUDIO_FILE = os.path.join(OUTPUT_DIR, "voice.wav")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)


def read_story():
    with open(STORY_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def split_scenes(text):
    sentences = [x.strip() for x in text.replace("\n", " ").split(".") if x.strip()]
    return sentences


def get_font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def create_scene(text, index):
    img = Image.new("RGB", (WIDTH, HEIGHT), "black")
    draw = ImageDraw.Draw(img)

    title_font = get_font(70)
    body_font = get_font(58)

    title = "FUNNY AI STORY"

    bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = bbox[2] - bbox[0]

    draw.text(
        ((WIDTH - title_width) / 2, 220),
        title,
        font=title_font,
        fill="white"
    )

    wrapped = textwrap.fill(text, width=25)

    bbox = draw.multiline_textbbox(
        (0, 0),
        wrapped,
        font=body_font,
        spacing=20
    )

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    draw.multiline_text(
        ((WIDTH - text_width) / 2, (HEIGHT - text_height) / 2),
        wrapped,
        font=body_font,
        fill="white",
        align="center",
        spacing=20
    )

    path = os.path.join(FRAMES_DIR, f"scene_{index:03d}.png")
    img.save(path)

    return path


def generate_voice(text):
    model = "/tmp/en_US-lessac-medium.onnx"

    if not os.path.exists(model):
        subprocess.run([
            "wget",
            "-q",
            "-O",
            model,
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
        ], check=True)

    config = model + ".json"

    if not os.path.exists(config):
        subprocess.run([
            "wget",
            "-q",
            "-O",
            config,
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
        ], check=True)

    process = subprocess.run(
        [
            "piper",
            "--model",
            model,
            "--output_file",
            AUDIO_FILE
        ],
        input=text,
        text=True,
        capture_output=True
    )

    if process.returncode != 0:
        print(process.stderr)
        raise RuntimeError("Voice generation failed.")


def render_video(scene_files):
    concat_file = "/tmp/scenes.txt"

    # Each scene lasts 4 seconds.
    with open(concat_file, "w") as f:
        for scene in scene_files:
            f.write(f"file '{scene}'\n")
            f.write("duration 4\n")

        # FFmpeg concat demuxer requires the final image again.
        if scene_files:
            f.write(f"file '{scene_files[-1]}'\n")

    subprocess.run([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-i", AUDIO_FILE,
        "-vf",
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2",
        "-r", str(FPS),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        VIDEO_FILE
    ], check=True)


def main():
    print("Reading story...")
    story = read_story()

    print("Creating scenes...")
    scenes = split_scenes(story)

    scene_files = []

    for i, scene in enumerate(scenes):
        print(f"Scene {i + 1}: {scene}")
        scene_files.append(create_scene(scene, i))

    print("Generating AI voice...")
    generate_voice(story)

    print("Rendering final video...")
    render_video(scene_files)

    print()
    print("=" * 50)
    print("VIDEO COMPLETE")
    print("=" * 50)
    print(VIDEO_FILE)


if __name__ == "__main__":
    main()
