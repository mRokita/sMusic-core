# -*- coding: utf-8 -*-
from protocol_utils import Binder
import logs
import cmus_utils
from exceptions import EXCEPTIONS
import config
from __init__ import __version__

binder = Binder()


@binder.bind()
def type():
    logs.print_info("Wykonano handshake! Łączenie z serwerem zakończone.")
    return {"request": "ok", "type": "radio", "key": config.server_key, "version": __version__}


@binder.bind()
def pause():
    cmus_utils.player_pause()
    return {"request": "ok", "status": cmus_utils.get_player_status()}


@binder.bind()
def status():
    stat = cmus_utils.get_player_status()
    stat["locked"] = not binder.gaps.is_unlocked()
    return {"request": "ok", "status": stat}


@binder.bind()
@binder.requires_unlocked()
def play():
    cmus_utils.player_play()
    return {"request": "ok", "status": cmus_utils.get_player_status()}


@binder.bind()
@binder.requires_unlocked()
def set_vol(value):
    cmus_utils.set_vol(value)
    return {"request": "ok"}


@binder.bind()
@binder.requires_unlocked()
def play_next():
    cmus_utils.player_next()
    return {"request": "ok", "status": cmus_utils.get_player_status()}


@binder.bind()
@binder.requires_unlocked()
def play_prev():
    cmus_utils.player_prev()
    return {"request": "ok", "status": cmus_utils.get_player_status()}


@binder.bind()
def get_artists():
    return {"request": "ok", "artists": [{"name": artist.name, "id": artist.id} for artist in
                                         sorted(binder.lib.get_artists().values(), key=lambda x: x.name)]}


@binder.bind()
def get_albums(artist=None):
    # album - [Album]
    if artist:
        lib_artist = binder.lib.get_artist(artist)
        albums = [{"name": album.name, "id": album.id} for album in sorted(lib_artist.get_albums(),
                                                                           key=lambda x: (int(x.year), x.name))]
        return {"request": "ok", "albums": albums, "artist_name": lib_artist.name}
    else:
        albums = [{"name": album.name, "id": album.id} for album in sorted(binder.lib.get_albums().values(),
                                                                           key=lambda x: (int(x.year), x.name))]
    return {"request": "ok", "albums": albums}


@binder.bind()
def add_to_queue(artist_id, album_id, track_id):
    cmus_utils.add_to_queue_from_lib(binder.lib, artist_id, album_id, track_id)
    return {"request": "ok", "queue": cmus_utils.get_queue()}


@binder.bind()
def clear_queue():
    cmus_utils.clear_queue()
    return {"request": "ok"}


@binder.bind()
@binder.requires_unlocked()
def set_queue_to_single_track(artist_id, album_id, track_id, start_playing=False):
    cmus_utils.clear_queue()
    cmus_utils.add_to_queue_from_lib(binder.lib, artist_id, album_id, track_id)
    cmus_utils.exec_cmus_command("set play_library=false")
    if start_playing:
        cmus_utils.player_next()
        cmus_utils.player_play()
    return {"request": "ok"}


@binder.bind()
def get_current_queue():
    q = cmus_utils.get_queue()
    tracks = []
    for path in q:
        logs.print_debug([path])
        track = binder.lib.get_track_by_filename(path)
        tracks.append({
            "artist_id": track.artist.id,
            "artist": track.artist.name,
            "title": track.title,
            "album_id": track.album.id,
            "album": track.album.name,
            "file": track.file,
            "id": track.id,
            "length": track.length,
            "length_readable": "0".join(("%2.2s:%2.2s" % (int(track.length // 60), int(track.length % 60))).split(" "))
        })
    return {"request": "ok", "queue": tracks}


@binder.bind()
def get_tracks(artist=None, album=None):
    tracks = []
    if artist and not album:
        lib_artist = binder.lib.get_artist(artist)
        tracks = [{"title": track.title, "id": track.id} for track in sorted(lib_artist.get_tracks(),
                                                                             key=lambda x: [int(x.tracknumber),
                                                                                            x.file])]
        return {"request": "ok", "tracks": tracks, "artist_name": lib_artist.name}
    if artist and album:
        lib_artist = binder.lib.get_artist(artist)
        lib_album = lib_artist.get_album(album)
        tracks = [{"title": track.title, "id": track.id} for track in sorted(lib_album.get_tracks(),
                                                                             key=lambda x: [x.tracknumber, x.file])]
        return {"request": "ok", "tracks": tracks, "artist_name": lib_artist.name, "album_name": lib_album.name}
    if not artist and not album:
        tracks = [{"title": track.title, "id": track.id} for track in sorted(binder.lib.get_tracks().values(),
                                                                             key=lambda x: [x.tracknumber, x.file])]
    return {"request": "ok", "tracks": tracks}


@binder.bind()
def error(type, comment, cat):
    logs.print_error("FATAL ERROR {}".format(cat))
    raise EXCEPTIONS[type](comment)


@binder.bind()
def search_for_track(query):
    return {"request": "ok",
            "tracks": [{"title": track.title,
                        "artist_name": track.artist.name,
                        "album_name": track.album.name,
                        "artist_id": track.artist.id,
                        "album_id": track.album.id,
                        "id": track.id} for track in binder.lib.search_for_track(query)]
            }
