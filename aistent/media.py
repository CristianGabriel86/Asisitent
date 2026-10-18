"""Procesare media locală cu Pillow și FFmpeg; fără generare AI implicită."""
import json
import math
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

RESOLUTIONS = {'480p': (854, 480), '720p': (1280, 720), '1080p': (1920, 1080)}


def run(command, timeout=120):
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
    except FileNotFoundError as error:
        raise ValueError('FFmpeg/FFprobe nu este instalat pe server.') from error
    except subprocess.TimeoutExpired as error:
        raise ValueError('Procesarea a depășit timpul disponibil. Folosește un clip mai scurt.') from error
    if result.returncode:
        # Do not leak internal filesystem paths or media metadata in errors.
        raise ValueError('Fișier media invalid sau operație incompatibilă cu acest fișier.')
    return result.stdout


def probe(path):
    data = json.loads(run(['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-show_format', '-show_streams', '-of', 'json', str(path)], 15))
    try:
        duration = float(data['format'].get('duration', 0))
        if not math.isfinite(duration) or not 0 < duration <= 300:
            raise ValueError
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video' and (stream.get('width', 0) > 4096 or stream.get('height', 0) > 4096):
                raise ValueError
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError('Sunt acceptate fișiere media de maximum 5 minute și rezoluție 4K.') from error
    return data


def number(value, minimum, maximum, label):
    try:
        result = float(value)
    except (ValueError, TypeError) as error:
        raise ValueError(f'{label}: valoare numerică invalidă.') from error
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise ValueError(f'{label}: valoarea trebuie să fie între {minimum} și {maximum}.')
    return result


def edit_photo(path, brightness=1, saturation=1, background=None):
    brightness = number(brightness, 0.1, 3, 'Luminozitate')
    saturation = number(saturation, 0, 3, 'Saturație')
    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert('RGBA')
            image.thumbnail((4096, 4096))
            if background:
                if len(background) != 7 or not background.startswith('#'):
                    raise ValueError('Culoare invalidă.')
                try:
                    color = tuple(int(background[index:index + 2], 16) for index in (1, 3, 5))
                except ValueError as error:
                    raise ValueError('Culoare invalidă.') from error
                canvas = Image.new('RGBA', image.size, (*color, 255))
                canvas.alpha_composite(image)
                image = canvas
            image = ImageEnhance.Brightness(image).enhance(brightness)
            image = ImageEnhance.Color(image).enhance(saturation)
            output = BytesIO()
            image.save(output, format='PNG')
            return output.getvalue()
    except (OSError, Image.DecompressionBombError) as error:
        raise ValueError('Imagine invalidă sau prea mare.') from error


def frames(path, count=6):
    info = probe(path)
    if not any(stream['codec_type'] == 'video' for stream in info['streams']):
        raise ValueError('Fișierul nu conține video.')
    duration = float(info['format']['duration'])
    result = []
    for index in range(count):
        timestamp = duration * (index + 0.5) / count
        data = run(['ffmpeg', '-v', 'error', '-nostdin', '-threads', '1', '-protocol_whitelist', 'file,pipe', '-ss', str(timestamp), '-i', str(path), '-frames:v', '1', '-vf', 'scale=768:768:force_original_aspect_ratio=decrease', '-f', 'image2pipe', '-vcodec', 'mjpeg', 'pipe:1'], 20)
        if data:
            result.append((timestamp, data))
    if not result:
        raise ValueError('Nu s-au putut extrage cadre din video.')
    return result


def video(paths, operation='trim', resolution='720p', start='0', end='', speed='1', brightness='0', saturation='1', music=None, subtitles=None):
    if resolution not in RESOLUTIONS or not paths or len(paths) > 8:
        raise ValueError('Alege o rezoluție validă și maximum 8 fișiere.')
    if operation not in {'trim', 'speed', 'color', 'concat', 'slideshow', 'audio', 'subtitles'}:
        raise ValueError('Operație video necunoscută.')
    width, height = RESOLUTIONS[resolution]
    normalize = f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24,format=yuv420p'
    command = ['ffmpeg', '-v', 'error', '-nostdin', '-y', '-filter_threads', '1', '-filter_complex_threads', '1']
    with tempfile.TemporaryDirectory(prefix='aistent-video-') as folder:
        output = Path(folder) / 'result.mp4'
        if operation in {'concat', 'slideshow'}:
            if len(paths) < 2:
                raise ValueError('Selectează cel puțin două fișiere în ordinea dorită.')
            filters = []
            total = 0
            for index, path in enumerate(paths):
                suffix = Path(path).suffix.lower()
                # Stored paths have opaque names: detect images through Pillow.
                try:
                    with Image.open(path) as image:
                        image.verify()
                    is_image = True
                except (OSError, Image.DecompressionBombError):
                    is_image = False
                if is_image:
                    command += ['-loop', '1', '-protocol_whitelist', 'file,pipe', '-i', str(path)]
                    duration = 3
                    filters.append(f'[{index}:v]trim=duration=3,setpts=PTS-STARTPTS,{normalize}[v{index}]')
                else:
                    info = probe(path)
                    total += float(info['format']['duration'])
                    if total > 300:
                        raise ValueError('Durata totală a montajului nu poate depăși 5 minute.')
                    command += ['-protocol_whitelist', 'file,pipe', '-i', str(path)]
                    filters.append(f'[{index}:v]setpts=PTS-STARTPTS,{normalize}[v{index}]')
            filters.append(''.join(f'[v{i}]' for i in range(len(paths))) + f'concat=n={len(paths)}:v=1:a=0[out]')
            command += ['-filter_complex', ';'.join(filters), '-map', '[out]', '-an']
        else:
            if len(paths) != 1:
                raise ValueError('Această operație necesită un singur videoclip.')
            info = probe(paths[0])
            if not any(stream['codec_type'] == 'video' for stream in info['streams']):
                raise ValueError('Selectează un fișier video.')
            duration = float(info['format']['duration'])
            start_value = number(start, 0, duration, 'Început')
            end_value = number(end or duration, 0, duration, 'Sfârșit')
            if end_value <= start_value:
                raise ValueError('Sfârșitul trebuie să fie după început.')
            speed_value = number(speed, 0.5, 2, 'Viteză') if operation == 'speed' else 1
            bright = number(brightness, -1, 1, 'Luminozitate') if operation == 'color' else 0
            sat = number(saturation, 0, 3, 'Saturație') if operation == 'color' else 1
            command += ['-protocol_whitelist', 'file,pipe', '-ss', str(start_value), '-i', str(paths[0])]
            vf = f'{normalize},setpts=PTS/{speed_value},eq=brightness={bright}:saturation={sat}'
            has_audio = any(stream['codec_type'] == 'audio' for stream in info['streams'])
            if operation == 'subtitles':
                if not subtitles:
                    raise ValueError('Selectează un fișier SRT.')
                caption = Path(folder) / 'captions.srt'
                text = Path(subtitles).read_text(encoding='utf-8-sig')
                if len(text) > 100000:
                    raise ValueError('Subtitrările sunt prea mari.')
                caption.write_text(text, encoding='utf-8')
                vf += f",subtitles=filename='{caption}'"
            if operation == 'audio':
                if not music:
                    raise ValueError('Selectează un fișier audio.')
                probe(music)
                command += ['-stream_loop', '-1', '-protocol_whitelist', 'file,pipe', '-i', str(music)]
                if has_audio:
                    command += ['-filter_complex', '[0:a][1:a]amix=inputs=2:duration=first:normalize=1[a]', '-map', '0:v:0', '-map', '[a]']
                else:
                    command += ['-map', '0:v:0', '-map', '1:a:0']
            else:
                command += ['-map', '0:v:0', '-map', '0:a:0?']
                if has_audio:
                    command += ['-af', f'atempo={speed_value}']
            command += ['-vf', vf, '-t', str((end_value - start_value) / speed_value)]
        command += ['-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '24', '-c:a', 'aac', '-movflags', '+faststart', '-fs', str(50 * 1024 * 1024), str(output)]
        run(command)
        if not output.exists() or output.stat().st_size >= 50 * 1024 * 1024:
            raise ValueError('Rezultatul este prea mare. Redu durata sau rezoluția.')
        probe(output)
        return output.read_bytes()
