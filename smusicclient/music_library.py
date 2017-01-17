# -*- coding: utf-8 -*-
import logging
from json import loads, dumps

import mutagen
from mutagen import File
from os import walk
from os.path import join
from whoosh import qparser
from whoosh.analysis import NgramWordAnalyzer
from whoosh.collectors import TimeLimitCollector, TimeLimit
from whoosh.fields import Schema, TEXT, ID
from whoosh.filedb.filestore import RamStorage
from whoosh.qparser import MultifieldParser
from whoosh.query import *
import string

PATTERN_DATE = re.compile("\d\d\d\d")


def id_from_tag(tag):
    tag = tag.lower()
    my_id = str()
    for char in tag:
        if char in string.ascii_lowercase + string.digits:
            my_id += char
    return my_id


def get_file_list(f_dir):
    tracks = []
    playlists = []
    for root, dirs, files in walk(f_dir):
        for file_name in files:
            if file_name.endswith(".smusicplaylist"):
                playlists.append(join(root, file_name))
                continue
            for extension in [".m4b", ".mp2", ".mp3", ".oga", ".ogg", ".mp4", ".m4a", ".aac", ".wav", ".webm", ".vox", ".tta", ".raw", ".ra", ".aax", ".3gp", ".aa", ".act", ".aiff", ".opus", ".flac", ".ape", ".amr", ".awb", ".dvf", ".dss", ".dct", ".gsm"]:
                if file_name.endswith(extension):
                    tracks.append(join(root, file_name))
    return tracks, playlists


def parse_library(lib_files):
    """
    Analizuje pliki podane w liście lib_files
    Zwraca instancję MusicLibrary
    """
    tracks, playlists = lib_files
    lib = MusicLibrary()
    lib_length = len(tracks)
    i = 0

    writer = lib.ix.writer()
    previous_procent_done_str = ""
    for f in tracks[:-1]:
        track_info = TrackInfo(f)
        lib.add_track_internal(track_info, writer)
        current_percent_done_str = "%d%%" % (i / lib_length * 100)
        if current_percent_done_str != previous_procent_done_str:
            logging.debug("Analizowanie biblioteki muzycznej... " + current_percent_done_str)
            previous_procent_done_str = current_percent_done_str
        i += 1.0
    logging.debug("Analizowanie playlist...")
    for f in playlists:
        with open(f, 'r') as fo:
            playlist_dict = loads(fo.read())
            playlist = Playlist(lib, f, playlist_dict['title'], playlist_dict['tracks'])
            lib.add_playlist(playlist)
    writer.commit()
    logging.debug("Optymalizacja index-u...")
    lib.ix.optimize()
    return lib

class Tag:
    def __init__(self, tags):
        if not tags:
            tags = {}
        defs = {"artist": "Nieznany wykonawca",
                "album": "Nieznany album",
                "title": None,
                "tracknumber": -1,
                "year": "0000",
                "date": "0000",
                "performer": "Nieznany wykonawca"
                }
        for key in defs:
            if key in tags and tags[key]:
                setattr(self, key, tags[key][0])
            elif key in defs:
                setattr(self, key, defs[key])
        if self.performer != defs["performer"] and self.artist == defs["artist"]:
            self.artist = self.performer
        date = PATTERN_DATE.findall(self.date)
        if date:
            setattr(self, "year", date[0])


class TrackInfo:
    def __init__(self, path):
        try:
            f = File(path, easy=True)
        except mutagen.MutagenError as e:
            logging.error("Couldn't parse tag for {}".format(path))
            logging.error(e)
            f = None
        try:
            self.length = f.info.length
        except AttributeError:
            self.length = None
        self.path = path
        self.tag = Tag(f)
        if not self.tag.title:
            self.tag.title = self.path


class Playlist:
    """
    Klasa reprezentująca playlistę
    """

    def __init__(self, library, file, name, tracks_list):
        self._tracks = list()
        self._library = library
        self.file = file
        self.id = id_from_tag(name)
        self.name = name
        logging.debug("Ładowanie playlisty \"{}\"...".format(self.name))
        for track_info in tracks_list:
            track = self._library.get_artist(track_info['artist_id']).get_album(track_info['album_id']).get_track(track_info['track_id'])
            if track:
                self._tracks.append(track)
            else:
                logging.warning("Nie znaleziono utworu \"{}\"".format(str(track_info)))
        logging.debug("Załadowano {} utworów!".format(len(self._tracks)))

    def get_tracks(self):
        return [track for track in self._tracks]

    def add_track(self, track):
        self._tracks.append(track)
        self.save()

    def del_track(self, index):
        del self._tracks[index]
        self.save()

    def to_dict(self):
        return{'title': self.name, 'tracks':
            [{'artist_id': t.artist.id, 'album_id': t.album.id, 'track_id': t.id} for t in self._tracks]}

    def save(self):
        with open(self.file, 'w+') as fo:
            fo.write(dumps(
                indent=4,
                data=self.to_dict()))

class Artist:
    """
    Klasa reprezentująca artystę
    """

    def __init__(self, library, name):
        self._albums = list()
        self._library = library
        self.id = id_from_tag(name)
        self.name = name
        self._tracks = list()

    def __str__(self):
        return "Artist(\"{}\", {})".format(self.name.encode("utf-8"), [str(album) for album in self._albums])

    def add_album(self, album):
        self._albums.append(album)

    def add_track(self, track):
        self._tracks.append(track)

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
     name - nazwa albumu [string]
     library - biblioteka [MusicLibrary]
     artist_id - nazwa artysty [string]
     year - rok [string -> int]
    """

    def __init__(self, library, artist_id, name, year):
        self._tracks = list()
        self._library = library
        self.id = id_from_tag(name)
        self.name = name
        self.artist = library.get_artist(artist_id)
        """:type : Artist"""
        self.artist.add_album(self)
        self.year = year

    def __str__(self):
        return "Album({}, {}, {})".format(self.name.encode("utf-8"), [str(track) for track in self._tracks], self.year)

    def add_track(self, track):
        self._tracks.append(track)
        self.artist.add_track(track)

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
    library - [MusicLirary]
    track - [TrackInfo]
    """

    def __init__(self, library, track):
        self.file = track.path
        self._library = library
        self.id = id_from_tag(track.tag.title)
        self.album = library.get_artist(id_from_tag(track.tag.artist)).get_album(id_from_tag(track.tag.album))
        """:type : Album"""
        self.artist = self.album.artist
        """:type : Artist"""
        self.title = track.tag.title
        self.length = track.length
        self.tracknumber = track.tag.tracknumber
        self.album.add_track(self)
        self.year = track.tag.year

    def __str__(self):
        return self.title.encode("utf-8")


class MusicLibrary:
    def __init__(self):
        self.__artists = dict()
        self.__albums = dict()
        self.__tracks = list()
        self.__playlists = list()
        analyzer = NgramWordAnalyzer(minsize=3)
        schema = Schema(title=TEXT(analyzer=analyzer, phrase=False), artist=TEXT(analyzer=analyzer, phrase=False),
                        album=TEXT(analyzer=analyzer, phrase=False), id=ID(stored=True))
        self.ram_storage = RamStorage()
        self.ram_storage.create()
        self.ix = self.ram_storage.create_index(schema)

    def add_track_internal(self, track_info, writer):

        artist_id = id_from_tag(track_info.tag.artist)

        if artist_id not in self.__artists:
            artist = (Artist(self, track_info.tag.artist))
            self.add_artist(artist)
        else:
            artist = self.__artists[artist_id]

        album_id = id_from_tag(track_info.tag.album)

        if album_id not in [a.id for a in artist.get_albums()]:
            album = Album(self, artist_id, track_info.tag.album, track_info.tag.year)
            if album.id not in self.__albums:
                self.__albums[album.id] = [album]
            else:
                self.__albums[album.id].append(album)
        track_id = id_from_tag(track_info.tag.title)

        if track_id not in [track.id for track in self.get_artist(artist_id).get_album(album_id).get_tracks()]:
            track = Track(self, track_info)
            self.__tracks.append(track)
            track_id = len(self.__tracks) - 1
            writer.add_document(title=unicode(track.title), artist=unicode(track.artist.name),
                                album=unicode(track.album.name), id=unicode(track_id))

    def add_playlist(self, playlist):
        self.__playlists.append(playlist)

    def get_playlist(self, playlist_name):
        id = id_from_tag(playlist_name)
        for p in self.__playlists:
            if p.id == id:
                return p
        return None

    def get_playlists(self):
        return [p for p in self.__playlists]

    def add_track(self, track_info):
        writer = self.ix.writer()
        self.add_track_internal(track_info, writer)
        writer.commit()

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

    def search_for_track(self, querystring):
        if len(querystring) >= 3:
            with self.ix.searcher() as searcher:
                collector = searcher.collector(limit=20)
                tlc = TimeLimitCollector(collector, timelimit=1.4, use_alarm=False)
                parser = MultifieldParser(["artist", "album", "title"], self.ix.schema)
                parser.add_plugin(qparser.FuzzyTermPlugin())
                myquery = parser.parse(querystring)
                try:
                    searcher.search_with_collector(myquery, tlc)
                    if len(tlc.results()) == 0:
                        myquery = parser.parse(" ".join(word + "~2" for word in querystring.split()))
                        searcher.search_with_collector(myquery, tlc)
                except TimeLimit:
                    logging.info("Time Limit for query reached!")
                logging.debug("czas zapytania: ", collector.runtime)
                ret = [self.__tracks[int(result["id"])] for result in tlc.results()]
                return ret
        else:
            return []

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
        for track in self.__tracks:
            if track.file == filename:
                return track
        logging.error("file %s not found in library" % filename)

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
