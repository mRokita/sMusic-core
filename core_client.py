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

binds = {}
PATTERN_MSG = re.compile("([ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789=+/]*?)\n(.+)?", re.DOTALL)


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
    return {"request": "ok", "type": "radio", "key": config.server_key}


@bind
def pause():
    cmus_utils.player_pause()
    return {"request": "ok", "status": cmus_utils.get_player_status()}


@bind
def status():
    return {"request": "ok", "status": cmus_utils.get_player_status()}


@bind
def play():
    cmus_utils.player_play()
    return {"request": "ok", "status": cmus_utils.get_player_status()}

@bind
def set_vol(value):
    cmus_utils.set_vol(value)
    return {"request": "ok"}


@bind
def play_next():
    cmus_utils.player_next()
    return {"request": "ok", "status": cmus_utils.get_player_status()}


@bind
def get_artists():
    return {"request": "ok", "artists": dict([(artist.name, artist.id) for artist in library.get_artists().values()])}


@bind
def get_albums(artist=None):
    if artist:

        albums = dict([(album.name, album.id) for album in library.get_artist(artist).get_albums()])
    else:
        albums = dict([(album.name, album.id) for album in library.get_albums().values()])
    return {"request": "ok", "albums": albums}


@bind
def get_tracks(artist=None, album=None):
    tracks = []
    if artist and not album:
        tracks = dict([(track.title, track.id) for track in library.get_artist(artist).get_tracks()])
    if artist and album:
        tracks = dict([(track.title, track.id) for track in library.get_artist(artist).get_album(album).get_tracks()])
    if not artist and not album:
        tracks = dict([(track.title, track.id) for track in library.get_tracks()])
    return {"request": "ok", "tracks": tracks}


if __name__ == "__main__":
    print "Analizowanie biblioteki..."
    library = cmus_utils.parse_current_library()
    print "\rZakończono analizowanie biblioteki."
    sys.stdout.write("Łączenie z serwerem...")
    conn = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    conn.connect((config.server_host, config.server_port))
    print "\rPołączono z serwerem!"
    print "Oczekiwanie na handshake..."
    msg = conn.read()
    buff = ""
    while msg:
        parsed_msg = PATTERN_MSG.findall(msg)
        if len(parsed_msg) == 1 and len(parsed_msg[0]) == 2:
            buff += parsed_msg[0][1]
            esc_string = parsed_msg[0][0]
            data = json.loads(un_escape(esc_string))
            if "request" in data:
                print "RECEIVED: %s" % data
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
        else:
            buff = ""
        msg = conn.read()
