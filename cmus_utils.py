# -*- coding: utf-8 -*-
"""
Moduł zawierający funkcje kontrolujące CMUSa
"""

from subprocess import check_output
import os
import re
from mutagen import File
import sys

TYPE_ARTIST = 1
TYPE_ALBUM = 2
TYPE_TRACK = 3

PATTERN_STATUS = re.compile("(?:tag|set)? ?([abcdefghijklmnopqrstuvxyz_]+) (.+)", re.DOTALL)


class ModifiedPlayedTrack(Exception):
    def __init__(self, msg):
        super(ModifiedPlayedTrack, self).__init__(msg)


class Tag:
    def __init__(self, tags):
        try:
            self.artist = tags["artist"][0]
            self.album = tags["album"][0]
            self.title = tags["title"][0]
        except Exception:
            self.artist = "<Unknown>"
            self.album = "<Unknown>"
            self.title = "<Unknown>"


class TrackInfo:
    def __init__(self, path):
        sys.stdout.write(path+"\r")
        f = File(path, easy=True)
        self.path = path
        self.tag = Tag(f)

class Artist:
        """
        Klasa reprezentująca artystę
        """
        def __init__(self, library, name):
            self._albums = list()
            self._library = library
            self.id = id_from_tag(name)
            self.name = name

        def __str__(self):
            return "Artist(\"{}\", {})".format(self.name.encode("utf-8"), [str(album) for album in self._albums])

        def add_album(self, album):
            self._albums.append(album)

        def get_album(self, album):
            album_id = id_from_tag(album)
            for album in self._albums:
                if album.id == album_id:
                    return album

        def get_albums(self):
            return self._albums


class Album:
    """
    Klasa reprezentująca album
    """
    def __init__(self, library, artist_id, name):
        self._tracks = list()
        self._library = library
        self.id = id_from_tag(name)
        self.name = name
        self.artist = library.get_artist(artist_id)
        self.artist.add_album(self)

    def __str__(self):
        return "Album({}, {})".format(self.name.encode("utf-8"), [str(track) for track in self._tracks])

    def add_track(self, track):
        self._tracks.append(track)

    def get_tracks(self):
        return list(self._tracks)

    def get_track(self, track):
        track_id = id_from_tag(track)
        for track in self._tracks:
            if track.id == track_id:
                return track


class Track:
    """
    Klasa reprezentująca utwór
    """
    def __init__(self, library, track):
        self.file = track.path
        self._library = library
        self.id = id_from_tag(track.tag.title)
        self.album = library.get_artist(id_from_tag(track.tag.artist)).get_album(id_from_tag(track.tag.album))
        self.artist = self.album.artist
        self.title = track.tag.title
        self.search_name = self.artist.id + self.album.id + self.id
        self.album.add_track(self)

    def __str__(self):
        return self.title.encode("utf-8")


class MusicLibrary:
    def __init__(self):
        self.__artists = dict()
        self.__albums = dict()
        self.__tracks = dict()

    def add_track(self, track_info):
        artist_id = id_from_tag(track_info.tag.artist)

        if artist_id not in self.__artists:
            artist = (Artist(self, track_info.tag.artist))
            self.add_artist(artist)
        else:
            artist = self.__artists[artist_id]

        album_id = id_from_tag(track_info.tag.album)

        if album_id not in [a.id for a in artist.get_albums()]:
            album = Album(self, artist_id, track_info.tag.album)
            if album.id not in self.__albums:
                self.__albums[album.id] = [album]
            else:
                self.__albums[album.id].append(album)
        track_id = id_from_tag(track_info.tag.title)

        if track_id not in [track.id for track in self.get_artist(artist_id).get_album(album_id).get_tracks()]:
            track = Track(self, track_info)
            self.__tracks[track.id] = track

    def add_artist(self, artist):
        self.__artists[artist.id] = artist

    def get_artist(self, artist):
        """
        Parametry: string artist - nazwa artysty
        Zwraca artystę o danej nazwie (wcześniej jest castowana przez id_from_tag)
        """
        try:
            return self.__artists[id_from_tag(artist)]
        except KeyError:
            return None

    def get_track(self, track):
        """
        Parametry: string artist - nazwa utworu
        Zwraca listę utworów o danej nazwie (wcześniej jest castowana przez id_from_tag)
        """
        try:
            return self.__tracks[id_from_tag(track)]
        except KeyError:
            return None

    def get_track_by_filename(self, filename):
        for track in self.__tracks.values():
            if track.file == filename:
                return track

    def get_album(self, album):
        """
        Parametry: string artist - nazwa utworu
        Zwraca listę albumów o danej nazwie (wcześniej jest castowana przez id_from_tag)
        """
        try:
            return self.__albums[id_from_tag(album)]
        except KeyError:
            return None

    def get_artists(self):
        return dict(self.__artists)

    def get_albums(self):
        return dict(self.__albums)

    def get_tracks(self):
        return dict(self.__tracks)


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
    os.remove("/tmp/sMusic_queue.m3u")
    with open("/tmp/sMusic_cached_queue.m3u", "w+") as fo:
        fo.write("\n".join(queue))


def get_queue():
    """
    Zwrot:
        - list<string> queue
    """
    exec_cmus_command("save -q /tmp/getqueue.m3u")
    q = get_queue_from_disk("/tmp/getqueue.m3u")
    os.remove("/tmp/getqueue.m3u")
    return q[:-1]


def get_cached_queue():
    """
    Zwraca zcache'owaną kolejkę
    """
    return get_queue_from_disk("/tmp/sMusic_cached_queue.pl")


def get_queue_from_disk(uri):
    with open(uri) as fo:
        q = fo.read()
    return q.split("\n")


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
    exec_cmus_command("save {}".format(path))
    with open(path) as fo:
        line = fo.readline()
        while line:
            lib.append(os.path.expanduser(line[:-1]))
            line = fo.readline()
    return lib


def id_from_tag(tag):
    tag = tag.lower()
    id = str()
    for char in tag:
        if char in "abcdefghijklmnopqrstuvwxyz1234567890":
            id += char
    return id


def parse_current_library():
    """
    Analizuje aktualną bibliotekę muzyczną CMUSa
    Zwraca instancję MusicLibrary
    """
    lib_files = get_current_library()
    lib = MusicLibrary()
    for file in lib_files[:-1]:
        track_info = TrackInfo(file)
        lib.add_track(track_info)
    return lib


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
