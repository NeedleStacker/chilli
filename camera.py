#camera.py
import subprocess

def capture_image(path):
    cmd = [
        'ffmpeg',
        '-f', 'v4l2',
        '-input_format', 'yuyv422',
        '-video_size', '1280x960',
        '-i', '/dev/video0',
        '-frames:v', '1',
        '-q:v', '2',
        '-y', path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
