import sys, subprocess, random
sys.path.insert(0, ".")
import podcast_generator as pg
from pathlib import Path

video_dir = Path("output/SAMPLE")
video_dir.mkdir(parents=True, exist_ok=True)

topic = random.choice(pg.TOPICS)
es, en = topic.split(" - ")[0], topic.split(" - ")[1]
turns = pg._fetch_turns_batch(topic, es, en, 0, 8)
if turns is None:
    raise SystemExit("batch fetch failed")

for f in video_dir.glob("*.png"):
    f.unlink(missing_ok=True)
for f in video_dir.glob("*.mp4"):
    f.unlink(missing_ok=True)

clips = []
for i, turn in enumerate(turns):
    img = video_dir / f"f_{i:04d}.png"
    pg.create_frame(turn, str(img), i)
    clip = video_dir / f"c_{i:04d}.mp4"
    audio = video_dir / f"a_{i:03d}.mp3"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "4", str(audio)], capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-i", str(audio),
        "-vf", "scale=1920:1080,fps=30", "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p", "-preset", "medium", "-t", "4", str(clip)], check=True, capture_output=True)
    clips.append(clip)

concat = video_dir / "list.txt"
with open(concat, "w") as f:
    for c in clips:
        f.write(f"file '{c.resolve().as_posix()}'\n")
out = video_dir / "sample_final.mp4"
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-movflags", "+faststart", str(out)], check=True)

for f in video_dir.glob("a_*.mp3"):
    f.unlink(missing_ok=True)
for f in video_dir.glob("c_*.mp4"):
    f.unlink(missing_ok=True)
concat.unlink(missing_ok=True)
for i in range(1, 8):
    (video_dir / f"f_{i:04d}.png").unlink(missing_ok=True)

print("SAMPLE:", out)
print("topic:", es)
for i, t in enumerate(turns[:4]):
    print(f"  [{i}] {t['speaker']}: {t['translit'][:70]}")