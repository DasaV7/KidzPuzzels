import os
import random
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, VideoClip, concatenate_videoclips

WIDTH, HEIGHT = 1280, 720
FPS = 24
PALETTE = ["#FCE4EC", "#E3F2FD", "#E8F5E9", "#FFF3E0", "#F3E5F5", "#E0F7FA"]
CARD_COLORS = ["#FF8A80", "#64B5F6", "#81C784"]
INK = "#263238"


def _font(size: int, bold: bool = True):
    candidates = [
        "assets/fonts/Poppins-Bold.ttf" if bold else "assets/fonts/Poppins-SemiBold.ttf",
        "assets/fonts/Montserrat-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_cover(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")
    scale = max(WIDTH / image.width, HEIGHT / image.height)
    resized = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - WIDTH) // 2
    top = (resized.height - HEIGHT) // 2
    return resized.crop((left, top, left + WIDTH, top + HEIGHT))


def _background(index: int, backgrounds: List[str]) -> Image.Image:
    if backgrounds:
        try:
            return _fit_cover(Image.open(backgrounds[index % len(backgrounds)]))
        except (OSError, ValueError):
            pass
    # Pastel fallback keeps the generator usable before custom art is added.
    top = (random.randint(220, 245), random.randint(225, 245), 255)
    bottom = (255, random.randint(235, 250), random.randint(220, 245))
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        color = tuple(int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
        draw.line((0, y, WIDTH, y), fill=color)
    return image


def _center_text(draw, text: str, y: int, font, fill=INK, stroke_width=0, stroke_fill="white"):
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    x = (WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


def _wrap_text(draw, text: str, font, max_width: int) -> List[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


def _question_slide(question: Dict[str, str], number: int, background: Image.Image,
                    output_path: str, reveal: bool = False) -> str:
    image = background.convert("RGBA")
    panel = Image.new("RGBA", image.size, (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel)
    panel_draw.rounded_rectangle((45, 35, 1235, 680), radius=42, fill=(255, 255, 255, 220),
                                 outline=(255, 255, 255, 245), width=4)
    image = Image.alpha_composite(image, panel)
    draw = ImageDraw.Draw(image)

    category = question.get("Category", "Fun Puzzle").strip() or "Fun Puzzle"
    draw.rounded_rectangle((85, 65, 360, 118), radius=24, fill="#7E57C2")
    draw.text((105, 75), category[:24], font=_font(27), fill="white")
    draw.text((1090, 76), f"{number:02d} / 10", font=_font(26), fill="#6A1B9A")

    prompt = question["Question"].strip()
    prompt_font = _font(51 if len(prompt) <= 47 else 42)
    lines = _wrap_text(draw, prompt, prompt_font, 1040)
    start_y = 150 if len(lines) <= 1 else 130
    for line_index, line in enumerate(lines[:2]):
        _center_text(draw, line, start_y + line_index * 62, prompt_font, fill="#263238")

    options = [("A", question["OptionA"].strip()), ("B", question["OptionB"].strip()),
               ("C", question["OptionC"].strip())]
    card_top, card_h, gap = 330, 116, 22
    for option_index, (letter, text) in enumerate(options):
        y = card_top + option_index * (card_h + gap)
        is_correct = text.casefold() == question["Correct"].strip().casefold()
        if reveal and is_correct:
            fill, outline, text_color, mark = "#C8E6C9", "#2E7D32", "#1B5E20", "✓"
        else:
            fill, outline, text_color, mark = "#FFFFFF", "#D1C4E9", INK, ""
        draw.rounded_rectangle((100, y, 1180, y + card_h), radius=28,
                               fill=fill, outline=outline, width=5 if reveal and is_correct else 3)
        draw.ellipse((125, y + 25, 190, y + 90), fill=CARD_COLORS[option_index])
        letter_font = _font(30)
        letter_box = draw.textbbox((0, 0), letter, font=letter_font)
        draw.text((157 - (letter_box[2] - letter_box[0]) // 2, y + 38), letter, font=letter_font, fill="white")
        draw.text((220, y + 33), text[:48], font=_font(38 if len(text) <= 27 else 31), fill=text_color)
        if mark:
            draw.text((1115, y + 25), mark, font=_font(54), fill="#2E7D32")

    if reveal:
        footer = f"Great thinking!  The answer is {question['Correct']}!"
        draw.rounded_rectangle((250, 625, 1030, 670), radius=20, fill="#FFF59D")
        footer_font = _font(25)
        bbox = draw.textbbox((0, 0), footer, font=footer_font)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) // 2, 632), footer, font=footer_font, fill="#5D4037")
    else:
        _center_text(draw, "Can you choose the right answer?", 631, _font(27, bold=False), fill="#5E35B1")

    image.convert("RGB").save(output_path, quality=94)
    return output_path


def _countdown_clip(image_path: str, duration: float):
    """Still puzzle slide with a smoothly advancing visible progress bar."""
    base = Image.open(image_path).convert("RGB")
    bar_left, bar_top, bar_width, bar_height = 110, 683, 1060, 14

    def make_frame(t):
        frame = base.copy()
        draw = ImageDraw.Draw(frame)
        draw.rounded_rectangle((bar_left, bar_top, bar_left + bar_width, bar_top + bar_height),
                               radius=7, fill="#EDE7F6")
        progress_width = int(bar_width * max(0.0, min(1.0, t / duration)))
        if progress_width:
            draw.rounded_rectangle((bar_left, bar_top, bar_left + progress_width, bar_top + bar_height),
                                   radius=7, fill="#7E57C2")
        return frame

    return VideoClip(make_frame=make_frame, duration=duration).set_fps(FPS).fadein(0.45).fadeout(0.35)


def _validate_question(row: Dict[str, str], index: int) -> None:
    required = ("Question", "OptionA", "OptionB", "OptionC", "Correct", "Category")
    missing = [key for key in required if not str(row.get(key, "")).strip()]
    if missing:
        raise ValueError(f"Question {index} is missing: {', '.join(missing)}")
    choices = [str(row[key]).strip().casefold() for key in ("OptionA", "OptionB", "OptionC")]
    if len(set(choices)) != 3:
        raise ValueError(f"Question {index} must have three distinct answer options.")
    if str(row["Correct"]).strip().casefold() not in choices:
        raise ValueError(f"Question {index}: Correct must match OptionA, OptionB, or OptionC.")


def _create_title_slide(title: str, subtitle: str, background: Image.Image, output_path: str) -> None:
    image = background.convert("RGBA")
    image = Image.alpha_composite(image, Image.new("RGBA", image.size, (255, 255, 255, 150)))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((90, 150, 1190, 570), radius=55, fill=(255, 255, 255, 225),
                           outline=(255, 255, 255, 255), width=4)
    _center_text(draw, title, 260, _font(74), fill="#6A1B9A", stroke_width=1, stroke_fill="white")
    _center_text(draw, subtitle, 390, _font(34, bold=False), fill="#37474F")
    for _ in range(45):
        x, y, radius = random.randint(35, WIDTH - 35), random.randint(35, HEIGHT - 35), random.randint(5, 11)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=random.choice(PALETTE))
    image.convert("RGB").save(output_path, quality=94)


def create_puzzle_video(questions: Iterable[Dict[str, str]], output_path: str = "generated/kids_puzzle_quiz.mp4",
                        answer_seconds: float = 2.5, intro_seconds: float = 4.0,
                        outro_seconds: float = 4.0) -> Tuple[str, Dict[str, list]]:
    """Render ten validated sheet questions as a 720p MP4; each question has 10 seconds to answer."""
    items = list(questions)
    if len(items) != 10:
        raise ValueError(f"A puzzle episode must contain exactly 10 questions (received {len(items)}).")
    for index, row in enumerate(items, start=1):
        _validate_question(row, index)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    os.makedirs("generated/slides", exist_ok=True)
    background_paths = sorted(
        str(path) for path in Path("assets/backgrounds").glob("*")
        if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    clips, used_images = [], []
    try:
        intro_path = "generated/slides/intro.png"
        _create_title_slide("Little Thinkers Quiz!", "10 fun questions • 3 choices • You can do it!",
                            _background(0, background_paths), intro_path)
        clips.append(ImageClip(intro_path).set_duration(intro_seconds).fadein(0.5).fadeout(0.35))
        used_images.append(os.path.basename(intro_path))

        for index, question in enumerate(items, start=1):
            bg = _background(index, background_paths)
            question_path = f"generated/slides/question_{index:02d}.png"
            answer_path = f"generated/slides/answer_{index:02d}.png"
            _question_slide(question, index, bg, question_path, reveal=False)
            _question_slide(question, index, bg, answer_path, reveal=True)
            clips.append(_countdown_clip(question_path, 10.0))
            clips.append(ImageClip(answer_path).set_duration(answer_seconds).fadein(0.35).fadeout(0.25))
            used_images.extend([os.path.basename(question_path), os.path.basename(answer_path)])

        outro_path = "generated/slides/outro.png"
        _create_title_slide("Fantastic job!", "Keep learning, keep smiling!", _background(11, background_paths), outro_path)
        clips.append(ImageClip(outro_path).set_duration(outro_seconds).fadein(0.45))
        used_images.append(os.path.basename(outro_path))

        final_video = concatenate_videoclips(clips, method="compose")
        try:
            final_video.write_videofile(output_path, fps=FPS, codec="libx264", audio=False,
                                        preset="medium", threads=2, logger=None,
                                        ffmpeg_params=["-pix_fmt", "yuv420p"])
        finally:
            final_video.close()
        return output_path, {"images": used_images, "videos": []}
    finally:
        for clip in clips:
            try:
                clip.close()
            except Exception:
                pass


def safe_video_filename(text: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip()).strip("_")
    return safe or "kids_puzzle_quiz"
