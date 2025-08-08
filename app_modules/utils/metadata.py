"""Funciones relacionadas con metadatos de archivos de audio"""
from typing import Dict, Optional
import requests

try:
    from mutagen.flac import FLAC
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC
    from mutagen import File
    MUTAGEN_AVAILABLE = True
except ImportError:  # pragma: no cover
    MUTAGEN_AVAILABLE = False
    print("Mutagen no disponible - funcionalidad de metadatos deshabilitada")


def add_metadata_to_file(file_path: str, track_info: Dict, cover_url: Optional[str] = None) -> bool:
    """Agregar metadatos básicos al archivo de audio si mutagen está disponible.

    track_info keys esperados: title, artist, album, year, track_number
    """
    if not MUTAGEN_AVAILABLE:
        return True

    try:
        audio_file = File(file_path)
        if audio_file is None:
            return False

        title = track_info.get('title', '')
        artist = track_info.get('artist', '')
        album = track_info.get('album', '')
        year = track_info.get('year', '')
        track_number = track_info.get('track_number', '')

        cover_data = None
        if cover_url:
            try:
                resp = requests.get(cover_url, timeout=10)
                if resp.status_code == 200:
                    cover_data = resp.content
            except Exception:
                pass

        if isinstance(audio_file, MP3):
            if audio_file.tags is None:
                audio_file.add_tags()
            audio_file.tags.add(TIT2(encoding=3, text=title))
            audio_file.tags.add(TPE1(encoding=3, text=artist))
            audio_file.tags.add(TALB(encoding=3, text=album))
            if year:
                audio_file.tags.add(TDRC(encoding=3, text=str(year)))
            if track_number:
                audio_file.tags.add(TRCK(encoding=3, text=str(track_number)))
            if cover_data:
                audio_file.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_data))
        elif isinstance(audio_file, FLAC):
            audio_file['TITLE'] = title
            audio_file['ARTIST'] = artist
            audio_file['ALBUM'] = album
            if year:
                audio_file['DATE'] = str(year)
            if track_number:
                audio_file['TRACKNUMBER'] = str(track_number)
            if cover_data:
                try:
                    from mutagen.flac import Picture
                    picture = Picture()
                    picture.type = 3
                    picture.mime = 'image/jpeg'
                    picture.desc = 'Cover'
                    picture.data = cover_data
                    audio_file.add_picture(picture)
                except Exception:
                    pass
        audio_file.save()
        return True
    except Exception:
        return False

__all__ = ["add_metadata_to_file", "MUTAGEN_AVAILABLE"]
