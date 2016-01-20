# -*- coding: utf-8 -*-
"""
Moduł zawierający funkcje kontrolujące CMUSa
"""

from subprocess import check_output
from os import remove
import re

PATTERN_STATUS = re.compile("(?:tag|set)? ?([abcdefghijklmnopqrstuvxyz_]+) (.+)", re.DOTALL)


class ModifiedPlayedTrack(Exception):
    def __init__(self, msg):
        super(ModifiedPlayedTrack, self).__init__(msg)


def exec_cmus_command(command):
    return check_output(["cmus-remote", "-C", command])


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
    output = check_output(["cmus-remote", "-Q"]).split("\n")
    status = dict()
    for line in output:
        match = PATTERN_STATUS.findall(line)
        if match:
            status[match[0][0]] = match[0][1]
    return status


def player_pause():
    exec_cmus_command("player-pause")


def player_play():
    exec_cmus_command("player-play")


def player_next():
    exec_cmus_command("player-next")


def player_prev():
    exec_cmus_command("player-prev")


def player_stop():
    exec_cmus_command("player-stop")


def set_vol(vol):
    exec_cmus_command("vol {0}%".format(vol))


def set_queue(queue, skip=0):
    """
    Parametry:
        - list<string> queue: kolejka w formie ["scieżka1", "sciezka2", "sciezka3"]
    Zmienia kolejkę na zawartość queue
    """
    exec_cmus_command("clear -q")
    with open("/tmp/sMusic_queue.m3u", "w+") as fo:
        fo.write("\n".join(queue[skip:]))
    exec_cmus_command("add -q {0}".format("/tmp/sMusic_queue.m3u"))
    remove("/tmp/sMusic_queue.m3u")
    with open("/tmp/sMusic_cached_queue.m3u", "w+") as fo:
        fo.write("\n".join(queue))


def get_queue():
    """
    Zwrot:
        - list<string> queue
    """
    exec_cmus_command("save -q /tmp/getqueue.m3u")
    q = get_queue_from_disk("/tmp/getqueue.m3u")
    remove("/tmp/getqueue.m3u")
    return q


def get_cached_queue():
    """
    Zwraca zcache'owaną kolejkę
    """
    return get_queue_from_disk("/tmp/sMusic_cached_queue.m3u")


def get_queue_from_disk(uri):
    with open(uri) as fo:
        q = fo.read()
    return q.split("\n")


def update_queue(q):
    """
    Parametry:
        - list<string> queue: kolejka w formie ["scieżka1", "sciezka2", "sciezka3"]
    Aktualizuje kolejkę i pomija odtworzone utwory
    """
    cached_queue = get_queue_from_disk("/tmp/sMusic_cached_queue.m3u")
    current_queue = get_queue()
    played_tracks_cnt = len(cached_queue)-len(current_queue)
    for i in range(played_tracks_cnt):
            if q[i] != cached_queue[i]:
                raise ModifiedPlayedTrack("{0}th track in queue has been modified".format(i))
    set_queue(q, played_tracks_cnt)

