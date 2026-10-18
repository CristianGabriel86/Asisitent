"""Fișiere media reale: FFmpeg, nu simulări ale procesării locale."""
import shutil
from pathlib import Path

import pytest
from PIL import Image

from aistent import media
from aistent.db import db
from test_workspace import upload


@pytest.fixture
def clip(tmp_path):
    assert shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Instalează FFmpeg și FFprobe pentru testele media obligatorii.'
    path = tmp_path / 'source.mp4'
    media.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-f', 'lavfi', '-i', 'testsrc=size=160x120:rate=12', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100', '-t', '2', '-filter_threads', '1', '-c:v', 'libx264', '-threads', '1', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(path)])
    return path


def check_result(tmp_path, data, duration, width=854):
    output = tmp_path / 'output.mp4'
    output.write_bytes(data)
    info = media.probe(output)
    assert abs(float(info['format']['duration']) - duration) < 0.4
    stream = next(stream for stream in info['streams'] if stream['codec_type'] == 'video')
    assert stream['width'] == width and stream['codec_name'] == 'h264'
    return info


def test_trim_speed_and_color(clip, tmp_path):
    check_result(tmp_path, media.video([clip], resolution='480p', start='0.5', end='1.5'), 1)
    info = check_result(tmp_path, media.video([clip], 'speed', '480p', speed='2'), 1)
    assert any(stream['codec_type'] == 'audio' for stream in info['streams'])
    check_result(tmp_path, media.video([clip], 'color', '480p', brightness='0.2', saturation='0'), 2)


def test_concat_video_and_photo_slideshow(clip, tmp_path):
    image = tmp_path / 'image.png'
    Image.new('RGB', (40, 40), 'green').save(image)
    check_result(tmp_path, media.video([clip, clip], 'concat', '480p'), 4)
    check_result(tmp_path, media.video([image, image], 'slideshow', '480p'), 6)
    check_result(tmp_path, media.video([clip, image], 'concat', '480p'), 5)


def test_audio_and_subtitles(clip, tmp_path):
    audio = tmp_path / 'sound.wav'
    media.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-f', 'lavfi', '-i', 'sine=frequency=880', '-t', '2', str(audio)])
    check_result(tmp_path, media.video([clip], 'audio', '480p', music=audio), 2)
    subtitle = tmp_path / 'subtitles.srt'
    subtitle.write_text('1\n00:00:00,000 --> 00:00:01,800\nText de verificare\n', encoding='utf-8')
    check_result(tmp_path, media.video([clip], 'subtitles', '480p', subtitles=subtitle), 2)


def test_sampled_frames_and_invalid_input(clip):
    frames = media.frames(clip, count=3)
    assert len(frames) == 3
    assert all(0 < time < 2.1 and data.startswith(b'\xff\xd8') for time, data in frames)
    with pytest.raises(ValueError):
        media.video([clip], 'speed', speed='nan')
    with pytest.raises(ValueError):
        media.video([clip], start='1.5', end='0.5')


def test_video_http_round_trip(client, project_id, clip):
    file_id = upload(client, project_id, 'filmare.mov', clip.read_bytes())
    response = client.post(f'/projects/{project_id}/video', data={'file_ids': file_id, 'operation': 'trim', 'resolution': '480p', 'start': '0', 'end': '1'})
    assert response.status_code == 302
    with client.application.app_context():
        output = db().execute("SELECT id FROM files WHERE name='montaj.mp4'").fetchone()[0]
    response = client.get(f'/files/{output}?preview=1', headers={'Range': 'bytes=0-127'})
    assert response.status_code == 206
    assert response.mimetype == 'video/mp4'
    assert len(response.data) == 128
