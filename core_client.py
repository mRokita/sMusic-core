#!/usr/bin/python2
# -*- coding: utf-8 -*-
"""
Bardzo minimalny testowy klient TCP
"""
import config
import socket
import ssl
import cmus_utils
import re
import sys
import json
from base64 import b64encode, b64decode
from inspect import getargspec
from threading import Thread
from functools import partial
import gaps_controller as gaps
import time

__version__ = "0.1.1 Alpha"
binds = {}
PATTERN_MSG = re.compile("([ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789=+/]*?)\n(.+)?", re.DOTALL)
was_interrupted = False
conn = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))


class InterruptionChecker:
    def __init__(self):
        self.__was_interrupted = False

    def wait_for_interruption(self):
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print "INTERRUPTION"
                self.__was_interrupted = True

    def was_interrupted(self):
        return self.__was_interrupted


class IncompatibleVersions(Exception):
    def __init__(self, msg):
        super(IncompatibleVersions, self).__init__(msg)


EXCEPTIONS = {
    u"incompatibleVersions": IncompatibleVersions
}


def escape(msg):
    return b64encode(msg)+"\n"


def un_escape(msg):
    return b64decode(msg)


def bind(function):
    argspec = getargspec(function)
    args = argspec[0]
    if argspec[-1]:
        req_args = args[:len(argspec[-1])-1]
    else:
        req_args = args
    binds[function.__name__] = {
        "target": function,
        "reqired_args": req_args,
        "args": args
    }
    return function


@bind
def type():
    print "\rWykonano handshake! Łączenie z serwerem zakończone."
    return {"request": "ok", "type": "radio", "key": config.server_key, "version": __version__}


@bind
def pause():
    cmus_utils.player_pause()
    return {"request": "ok", "status": cmus_utils.get_player_status()}


@bind
def status():
    stat = cmus_utils.get_player_status()
    stat["locked"] = not gaps.is_unlocked()
    return {"request": "ok", "status": stat}


@bind
@gaps.requires_unlocked
def play():
    cmus_utils.player_play()
    return {"request": "ok", "status": cmus_utils.get_player_status()}

@bind
def set_vol(value):
    cmus_utils.set_vol(value)
    return {"request": "ok"}


@bind
@gaps.requires_unlocked
def play_next():
    cmus_utils.player_next()
    return {"request": "ok", "status": cmus_utils.get_player_status()}


@bind
@gaps.requires_unlocked
def play_prev():
    cmus_utils.player_prev()
    return {"request": "ok", "status": cmus_utils.get_player_status()}


@bind
def get_artists():
    return {"request": "ok", "artists": [{"name": artist.name, "id": artist.id} for artist in sorted(library.get_artists().values(), key=lambda x: x.name)]}


@bind
def get_albums(artist=None):
    # album - [Album]
    if artist:
        lib_artist = library.get_artist(artist)
        albums = [{"name": album.name, "id": album.id} for album in sorted(lib_artist.get_albums(),
                                                                            key=lambda x: (x.date, x.name))]
        return {"request": "ok", "albums": albums, "artist_name": lib_artist.name}
    else:
        albums = [{"name": album.name, "id": album.id} for album in sorted(library.get_albums().values(),
                                                                            key=lambda x: (x.date, x.name))]
    return {"request": "ok", "albums": albums}


@bind
def add_to_queue(artist_id,album_id, track_id):
    cmus_utils.add_to_queue_from_lib(library, artist_id, album_id, track_id)
    return {"request": "ok", "queue": cmus_utils.get_queue()}


@bind
def clear_queue():
    cmus_utils.clear_queue()
    return {"request": "ok"}


@bind
@gaps.requires_unlocked
def set_queue_to_single_track(artist_id, album_id, track_id, start_playing=False):
    cmus_utils.clear_queue()
    cmus_utils.add_to_queue_from_lib(library, artist_id, album_id, track_id)
    cmus_utils.exec_cmus_command("set play_library=false")
    if start_playing:
        cmus_utils.player_next()
        cmus_utils.player_play()
    return {"request": "ok"}


@bind
def get_current_queue():
    q = cmus_utils.get_queue()
    tracks = []
    for path in q:
        print [path]
        track = library.get_track_by_filename(path)
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


@bind
def get_tracks(artist=None, album=None):
    tracks = []
    if artist and not album:
        lib_artist = library.get_artist(artist)
        tracks = [{"title": track.title, "id": track.id} for track in sorted(lib_artist.get_tracks(),
                                                                             key=lambda x: [int(x.tracknumber), x.file])]
        return {"request": "ok", "tracks": tracks, "artist_name": lib_artist.name}
    if artist and album:
        lib_artist = library.get_artist(artist)
        lib_album = lib_artist.get_album(album)
        tracks = [{"title": track.title, "id": track.id} for track in sorted(lib_album.get_tracks(),
                                                                             key=lambda x: [x.tracknumber, x.file])]
        return {"request": "ok", "tracks": tracks, "artist_name": lib_artist.name, "album_name": lib_album.name}
    if not artist and not album:
        tracks = [{"title": track.title, "id": track.id} for track in sorted(library.get_tracks().values(),
                                                                             key=lambda x: [x.tracknumber, x.file])]
    return {"request": "ok", "tracks": tracks}


@bind
def error(type, comment, cat):
    conn.close()
    print "FATAL ERROR {}".format(cat)
    raise EXCEPTIONS[type](comment)


@bind
def search_for_track(query):
    return {"request": "ok",
            "tracks": [{"title": track.title,
                        "artist_name": track.artist.name,
                        "album_name": track.album.name,
                        "artist_id": track.artist.id,
                        "album_id": track.album.id,
                        "id": track.id} for track in library.search_for_track(query)]
            }


def handle_message(data, conn):
    target = binds[data["request"]]["target"]
    datacpy = dict(data)
    del datacpy["request"]
    if "msgid" in datacpy:
        del datacpy["msgid"]
    ret = target(**datacpy)
    if "msgid" in data:
        ret["msgid"] = data["msgid"]
    print "RETURNING: %s" % ret
    conn.send(escape(json.dumps(ret)))


class ConnectionThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.__was_stopped = False
        sys.stdout.write("Łączenie z serwerem...")
        self.conn = conn
        self.conn.connect((config.server_host, config.server_port))
        print "\rPołączono z serwerem!"

    def run(self):
        print "Oczekiwanie na handshake..."
        buff = ""
        msg = conn.read()
        while msg and not self.__was_stopped:
            parsed_msg = PATTERN_MSG.findall(msg)
            if len(parsed_msg) == 1 and len(parsed_msg[0]) == 2:
                buff += parsed_msg[0][1]
                esc_string = parsed_msg[0][0]
                data = json.loads(un_escape(esc_string))
                print "RECEIVED: %s" % data
                if "request" in data:
                    Thread(target=partial(handle_message, data, conn)).start()
            else:
                buff = ""
            msg = conn.read()

    def stop(self):
        self.__was_stopped = True
        conn.close()


if __name__ == "__main__":
    print "+---------------------------------------------+\n|"+\
          ("sMusic-core v{}".format(__version__).center(45, " "))+"|\n|"+\
          ("https://github.com/mRokita/sMusic-core").center(45, " ")+\
          "|\n+---------------------------------------------+\n"
    library = cmus_utils.parse_current_library()
    print "\rZakończono analizowanie biblioteki."
    print "Ładowanie przerw..."
    gaps.load_gaps()
    thread_gap = gaps.GapThread()
    thread_gap.start()
    thread_conn = ConnectionThread()
    thread_conn.start()
    try:
        while True:
            time.sleep(100)
    except (KeyboardInterrupt, SystemExit):
        print "\nZatrzymywanie kontroli przerw..."
        thread_gap.stop()
        print "Zatrzymano kontrolę przerw!\nRozłączanie z serwerem..."
        thread_conn.stop()
        print "Rozłączono z serwerem!"


