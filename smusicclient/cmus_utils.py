# -*- coding: utf-8 -*-
"""
Moduł zawierający funkcje kontrolujące CMUSa
"""

from subprocess import check_output
import os
from musiclibrary import *
import re
import os.path

TYPE_ARTIST = 1
TYPE_ALBUM = 2
TYPE_TRACK = 3

PATTERN_STATUS = re.compile("(?:tag|set)? ?([abcdefghijklmnopqrstuvxyz_]+) (.+)", re.DOTALL)

cmus_remote_env = os.environ.copy()
if (not "HOME" in cmus_remote_env) or cmus_remote_env["HOME"] == str():
    cmus_remote_env["HOME"] = "/root"
if (not "USER" in cmus_remote_env) or cmus_remote_env["USER"] == str():
    cmus_remote_env["USER"] = "root"


class ModifiedPlayedTrack(Exception):
    def __init__(self, msg):
        super(ModifiedPlayedTrack, self).__init__(msg)


def exec_cmus_command(command):
    return check_output(["cmus-remote", "-C", command], env=cmus_remote_env)


def get_player_status():
    """
    Zwraca słownik z informacjami o statusie odtwarzacza:
        dict: {
            "comment": "TPB FTW!",
            "shuffle": "false",
            "vol_left": "100",
            "replaygain_preamp": "0.000000",
            "genre": "General Alternative Rock",
            "replaygain": "disabled",
            "albumartist": "Artur Rojek",
            "file": "/muzyka/Artur Rojek - Składam się z ciągłych powtórzeń [2014] [FLAC]/02 - Artur Rojek - Beksa.flac",
            "duration": "241",
            "tracknumber": "2",
            "aaa_mode": "album",
            "album": "Składam się z ciągłych powtórzeń",
            "vol_right": "100",
            "replaygain_album_gain": "-8.44 dB",
            "title": "Beksa",
            "repeat_current": "false",
            "play_library": "true",
            "replaygain_track_gain": "-9.72 dB",
            "softvol": "false",
            "replaygain_album_peak": "1.000000",
            "status": "playing",
            "repeat": "true",
            "replaygain_limit": "true",
            "date": "2014",
            "discnumber": "1",
            "play_sorted": "false",
            "artist": "Artur Rojek",
            "replaygain_track_peak": "0.988403",
            "continue": "true",
            "position": "108"
        }
    """
    output = check_output(["cmus-remote", "-Q"], env=cmus_remote_env).split("\n")
    status = dict()
    for line in output:
        match = PATTERN_STATUS.findall(line)
        if match:
            status[match[0][0]] = match[0][1]
    if "duration" in status:
        duration = int(status["duration"])
        status["duration_readable"] = "0".join(("%2.2s:%2.2s" % (int(duration // 60), int(duration % 60))).split(" "))
    return status


def is_playing():
    return get_player_status()["status"] == "playing"


def player_pause():
    if get_player_status()["status"] != "paused":
        exec_cmus_command("player-pause")


def player_play():
    if get_player_status()["status"] != "playing":
        exec_cmus_command("player-play")


def player_next():
    exec_cmus_command("player-next")


def player_prev():
    exec_cmus_command("player-prev")


def player_stop():
    exec_cmus_command("player-stop")


def set_vol(vol):
    exec_cmus_command("vol {0}%".format(vol))


def add_to_queue(path):
    exec_cmus_command("add -q {}".format(path))


def add_to_queue_from_lib(lib, artist_id, album_id, track_id):
    track = lib.get_artist(artist_id).get_album(album_id).get_track(track_id)
    add_to_queue(track.file)


def clear_queue():
    exec_cmus_command("clear -q")


def set_queue(queue):
    """
    Parametry:
        - list<string> queue: kolejka w formie ["scieżka1", "sciezka2", "sciezka3"]
    Zmienia kolejkę na zawartość queue
    """
    clear_queue()
    for path in queue:
        add_to_queue(path)


def get_queue():
    """
    Zwrot:
        - list<string> queue
    """
    exec_cmus_command("save -q /tmp/getqueue.m3u")
    q = get_queue_from_disk("/tmp/getqueue.m3u")
    os.remove("/tmp/getqueue.m3u")
    return q


def get_queue_from_disk(uri):
    with open(uri) as fo:
        q = fo.read()
    return q.split("\n")[:-1]


def get_current_library():
    """
    Zdobywa listę ścieżek do utworów w bibliotece CMUSa
    Zwraca list<string> złożoną ścieżek
    """
    if os.path.exists(os.path.expanduser("~/.config/cmus/")):
        path = os.path.expanduser("~/.config/cmus/lib.pl")
    elif os.path.exists(os.path.expanduser("~/.cmus/")):
        path = os.path.expanduser("~/.cmus/lib.pl")
    else:
        return list()
    lib = list()
    exec_cmus_command("save -l {}".format(path))
    with open(path) as fo:
        line = fo.readline()
        while line:
            lib.append(os.path.expanduser(line[:-1]))
            line = fo.readline()
    return lib


def get_musiclibrary():
    lib_files = get_current_library()
    return parse_library(lib_files)


def update_queue(q):
    """
    Parametry:
        - list<string> queue: kolejka w formie ["scieżka1", "sciezka2", "sciezka3"]
    Aktualizuje kolejkę i pomija odtworzone utwory
    """
    cached_queue = get_queue_from_disk("/tmp/sMusic_cached_queue.pl")
    current_queue = get_queue()
    played_tracks_cnt = len(cached_queue) - len(current_queue)
    for i in range(played_tracks_cnt):
            if q[i] != cached_queue[i]:
                raise ModifiedPlayedTrack("{0}th track in queue has been modified".format(i))
    set_queue(q, played_tracks_cnt)
