import subprocess
import logging

def capture_image(path: str) -> bool:
    """
    Captures an image from a V4L2 device using ffmpeg.

    Args:
        path (str): The file path where the image will be saved.

    Returns:
        bool: True if the image was captured successfully, False otherwise.
    """
    command = [
        'ffmpeg',
        '-f', 'v4l2',
        '-input_format', 'yuyv422',
        '-video_size', '1280x960',
        '-i', '/dev/video0',
        '-frames:v', '1',
        '-q:v', '2',
        '-y', path
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        logging.info(f"Image captured successfully and saved to {path}")
        return True
    except FileNotFoundError:
        logging.error("ffmpeg command not found. Please ensure ffmpeg is installed and in your PATH.")
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"ffmpeg failed with exit code {e.returncode}")
        logging.error(f"ffmpeg stderr: {e.stderr.decode().strip()}")
        return False
