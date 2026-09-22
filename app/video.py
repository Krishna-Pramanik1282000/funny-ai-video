import os
import subprocess
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# FUNNY AI VIDEO GENERATOR - PHASE 1
# ============================================================

# Automatically find the repository directory.
BASE_DIR = Path(__file__).resolve().parent.parent

STORY_FILE = BASE_DIR / "input" / "story.txt"
OUTPUT_DIR = BASE_DIR / "output"
FRAMES_DIR = Path("/tmp/funny_ai_frames")

VIDEO_FILE = OUTPUT_DIR / "funny_video.mp4"
AUDIO_FILE = OUTPUT_DIR / "voice.wav"

WIDTH = 1080
HEIGHT = 1920
FPS = 30

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FONT
# ============================================================

def get_font(size):
    fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for font_path in fonts:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)

    return ImageFont.load_default()


# ============================================================
# READ STORY
# ============================================================

def read_story():
    if not STORY_FILE.exists():
        raise FileNotFoundError(
            f"Story file not found: {STORY_FILE}"
        )

    story = STORY_FILE.read_text(encoding="utf-8").strip()

    if not story:
        raise ValueError("story.txt is empty.")

    return story


# ============================================================
# SPLIT STORY INTO SCENES
# ============================================================

def split_scenes(text):
    # Convert new lines into spaces.
    text = text.replace("\n", " ")

    # Split sentences.
    sentences = [
        sentence.strip()
        for sentence in text.replace("!", ".").replace("?", ".").split(".")
        if sentence.strip()
    ]

    return sentences


# ============================================================
# CREATE SCENE IMAGE
# ============================================================

def create_scene(text, index):

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        "black"
    )

    draw = ImageDraw.Draw(image)

    title_font = get_font(70)
    body_font = get_font(58)

    # Title
    title = "FUNNY AI STORY"

    title_box = draw.textbbox(
        (0, 0),
        title,
        font=title_font
    )

    title_width = title_box[2] - title_box[0]

    draw.text(
        (
            (WIDTH - title_width) / 2,
            200
        ),
        title,
        font=title_font,
        fill="white"
    )

    # Scene text
    wrapped_text = textwrap.fill(
        text,
        width=25
    )

    text_box = draw.multiline_textbbox(
        (0, 0),
        wrapped_text,
        font=body_font,
        spacing=20
    )

    text_width = text_box[2] - text_box[0]
    text_height = text_box[3] - text_box[1]

    draw.multiline_text(
        (
            (WIDTH - text_width) / 2,
            (HEIGHT - text_height) / 2
        ),
        wrapped_text,
        font=body_font,
        fill="white",
        align="center",
        spacing=20
    )

    # Scene number
    scene_label = f"Scene {index + 1}"

    draw.text(
        (40, HEIGHT - 100),
        scene_label,
        font=get_font(40),
        fill="white"
    )

    output = FRAMES_DIR / f"scene_{index:03d}.png"

    image.save(output)

    return output


# ============================================================
# GENERATE AI VOICE WITH PIPER
# ============================================================

def generate_voice(text):

    model = Path("/tmp/en_US-lessac-medium.onnx")

    model_url = (
        "https://huggingface.co/rhasspy/piper-voices/"
        "resolve/main/en/en_US/lessac/medium/"
        "en_US-lessac-medium.onnx"
    )

    config_url = (
        "https://huggingface.co/rhasspy/piper-voices/"
        "resolve/main/en/en_US/lessac/medium/"
        "en_US-lessac-medium.onnx.json"
    )

    config = Path(str(model) + ".json")

    print("Checking Piper voice model...")

    if not model.exists():

        print("Downloading Piper voice model...")

        subprocess.run(
            [
                "wget",
                "-q",
                "--show-progress",
                "-O",
                str(model),
                model_url
            ],
            check=True
        )

    if not config.exists():

        print("Downloading Piper voice configuration...")

        subprocess.run(
            [
                "wget",
                "-q",
                "--show-progress",
                "-O",
                str(config),
                config_url
            ],
            check=True
        )

    print("Generating AI narration...")

    result = subprocess.run(
        [
            "piper",
            "--model",
            str(model),
            "--output_file",
            str(AUDIO_FILE)
        ],
        input=text,
        text=True,
        capture_output=True
    )

    if result.returncode != 0:

        print(result.stdout)
        print(result.stderr)

        raise RuntimeError(
            "Piper voice generation failed."
        )

    if not AUDIO_FILE.exists():
        raise RuntimeError(
            "Voice file was not created."
        )

    print(
        f"Voice created: {AUDIO_FILE}"
    )


# ============================================================
# CREATE VIDEO
# ============================================================

def render_video(scene_files):

    concat_file = Path("/tmp/scenes.txt")

    print("Preparing FFmpeg scene list...")

    with concat_file.open("w", encoding="utf-8") as file:

        for scene in scene_files:

            file.write(
                f"file '{scene}'\n"
            )

            file.write(
                "duration 4\n"
            )

        # Required by concat demuxer.
        if scene_files:
            file.write(
                f"file '{scene_files[-1]}'\n"
            )

    print("Rendering video...")

    subprocess.run(
        [
            "ffmpeg",
            "-y",

            "-f",
            "concat",

            "-safe",
            "0",

            "-i",
            str(concat_file),

            "-i",
            str(AUDIO_FILE),

            "-vf",
            (
                f"scale={WIDTH}:{HEIGHT}:"
                "force_original_aspect_ratio=decrease,"
                f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2"
            ),

            "-r",
            str(FPS),

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-pix_fmt",
            "yuv420p",

            "-c:a",
            "aac",

            "-shortest",

            str(VIDEO_FILE)
        ],
        check=True
    )

    if not VIDEO_FILE.exists():
        raise RuntimeError(
            "FFmpeg did not create the final video."
        )

    print(
        f"Video created: {VIDEO_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("FUNNY AI VIDEO GENERATOR")
    print("=" * 60)

    print(f"Repository: {BASE_DIR}")
    print(f"Story:      {STORY_FILE}")
    print(f"Output:     {OUTPUT_DIR}")

    print("\n1. Reading story...")

    story = read_story()

    print(
        f"Story length: {len(story)} characters"
    )

    print("\n2. Creating scenes...")

    scenes = split_scenes(story)

    if not scenes:
        raise RuntimeError(
            "No scenes were detected."
        )

    print(
        f"Detected {len(scenes)} scenes."
    )

    scene_files = []

    for index, scene in enumerate(scenes):

        print(
            f"Creating scene {index + 1}: {scene}"
        )

        scene_file = create_scene(
            scene,
            index
        )

        scene_files.append(scene_file)

    print("\n3. Generating narration...")

    generate_voice(story)

    print("\n4. Rendering final MP4...")

    render_video(scene_files)

    print("\n" + "=" * 60)
    print("SUCCESS!")
    print("=" * 60)

    print(
        f"\nFinal video:\n{VIDEO_FILE}"
    )

    print(
        f"\nFile size: "
        f"{VIDEO_FILE.stat().st_size / 1024 / 1024:.2f} MB"
    )


if __name__ == "__main__":
    main()
