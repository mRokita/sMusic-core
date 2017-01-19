# -*- coding: utf-8 -*-
import config
import download_controller
import logs
from __init__ import __version__
from exceptions import EXCEPTIONS
from protocol_utils import Binder

binder = Binder()


@binder.bind()
def type():
    logs.print_info("Wykonano handshake! Łączenie z serwerem zakończone.")
    return {"request": "ok", "type": "radio", "key": config.server_key, "version": __version__}


@binder.bind()
def pause():
    binder.player.pause()
    return {"request": "ok", "status": binder.player.get_json_status()}


@binder.bind()
def status():
    stat = binder.player.get_json_status()
    stat["locked"] = not binder.gaps.is_unlocked()
    return {"request": "ok", "status": stat}


@binder.bind()
@binder.requires_unlocked()
def play():
    binder.player.play()
    return {"request": "ok", "status": binder.player.get_json_status()}


@binder.bind()
def seek(position):
    binder.player.seek(int(position))
    return {"request": "ok"}


@binder.bind()
def set_vol(value):
    binder.player.set_volume(int(value))
    return {"request": "ok"}


@binder.bind()
@binder.requires_unlocked()
def play_next():
    binder.player.next_track()
    return {"request": "ok", "status": binder.player.get_json_status()}


@binder.bind()
@binder.requires_unlocked()
def play_prev():
    binder.player.prev_track()
    return {"request": "ok", "status": binder.player.get_json_status()}


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
def move_queue_item(source_index, dest_index):
    binder.player.move_queue_item(int(source_index), int(dest_index))
    return get_current_queue()


@binder.bind()
def add_to_queue(artist_id, album_id, track_id):
    binder.player.add_to_queue(binder.lib.get_artist(artist_id).get_album(album_id).get_track(track_id))
    return {"request": "ok"}


@binder.bind()
@binder.requires_unlocked()
def set_queue_position(pos):
    binder.player.set_queue_position(int(pos))
    binder.player.play()
    return get_current_queue()


@binder.bind()
def del_from_queue(pos):
    binder.player.del_from_queue(int(pos))
    return get_current_queue()


@binder.bind()
@binder.requires_unlocked()
def add_playlist_to_queue(playlist_id):
    playlist = binder.lib.get_playlist(playlist_id)
    for t in playlist.get_tracks():
        binder.player.add_to_queue(t)
    return {"request": "ok"}


@binder.bind()
def set_queue_to_playlist(playlist_id, start_playing=False):
    playlist = binder.lib.get_playlist(playlist_id)
    binder.player.clear_queue()
    for i, t in enumerate(playlist.get_tracks()):
        binder.player.add_to_queue(t)

    if start_playing:
        binder.player.play()
    return {"request": "ok"}


@binder.bind()
def get_playlist(playlist_id):
    playlist = binder.lib.get_playlist(playlist_id)
    return {"request": "ok", "playlist": playlist.to_www()}


@binder.bind()
def create_playlist(playlist_name):
    playlists = binder.lib.create_playlist(playlist_name)
    return {"request": "ok", "playlists": [p.to_www() for p in playlists]}


@binder.bind()
def change_playlist_order(playlist_id, source_index, dest_index):
    p = binder.lib.get_playlist(playlist_id)
    p.move_track(int(source_index), int(dest_index))
    return {"request": "ok", "playlist": p.to_www()}


@binder.bind()
def del_playlist(playlist_id):
    binder.lib.del_playlist(playlist_id)
    return {"request": "ok"}


@binder.bind()
def add_track_to_playlist(playlist_id, artist_id, album_id, track_id):
    playlist = binder.lib.get_playlist(playlist_id)
    track = binder.lib.get_artist(artist_id).get_album(album_id).get_track(track_id)
    playlist.add_track(track)
    return {"request": "ok"}


@binder.bind()
def del_track_from_playlist(playlist_id, track_num):
    playlist = binder.lib.get_playlist(playlist_id)
    playlist.del_track(int(track_num))
    return {"request": "ok", "playlist": playlist.to_www()}


@binder.bind()
def get_playlists():
    return {"request": "ok", "playlists": [p.to_www() for p in binder.lib.get_playlists()]}


@binder.bind()
def clear_queue():
    binder.player.clear_queue()
    return {"request": "ok"}


@binder.bind()
@binder.requires_unlocked()
def set_queue_to_single_track(artist_id, album_id, track_id, start_playing=False):
    binder.player.clear_queue()
    binder.player.add_to_queue(binder.lib.get_artist(artist_id).get_album(album_id).get_track(track_id))
    if start_playing:
        binder.player.play()
    return {"request": "ok"}


@binder.bind()
def get_current_queue():
    q = binder.player.get_queue()
    tracks = []
    for i, track in enumerate(q):
        tracks.append({
            "artist_id": track.artist.id,
            "artist": track.artist.name,
            "title": track.title,
            "album_id": track.album.id,
            "album": track.album.name,
            "file": track.file,
            "is_current": binder.player.get_queue_position() == i,
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
def add_download(url, artist="", album="", track=""):
    try:
        download_controller.thread.add_download(url, artist, album, track)
        return {"request": "ok"}
    except Exception as e:
        return {"request": "error", "cat": "=^..^=", "comment": "exception while trying to download: %s" % e}


@binder.bind()
def download_status():
    ret = download_controller.thread.get_status()
    ret["request"] = "ok"
    return ret


@binder.bind()
def get_download_queue():
    queue = []
    for item in download_controller.thread.get_queue():
        queue.append({"url": item.url, "artist": item.artist, "album": item.album, "track": item.track})
    return {"request": "ok", "queue": queue}


@binder.bind()
def clear_download_queue():
    download_controller.thread.clear_queue()
    return {"request": "ok"}


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


@binder.bind()
def ping():
    logs.print_debug("Ping")
    return {"request": "ok"}
