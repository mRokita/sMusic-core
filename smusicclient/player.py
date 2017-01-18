# -*- coding: utf-8 -*-
from alsaaudio import Mixer
from threading import Thread

from pyaudio import PyAudio
from pydub import AudioSegment
from pydub.utils import make_chunks

import config
import music_library

mixer = Mixer(cardindex=config.cardindex)
lib = None


class Stream(Thread):
    def __init__(self, f, on_terminated):
        self.__active = True
        self.__path = f
        self.__paused = True
        self.on_terminated = on_terminated
        self.__position = 0
        self.__chunks = []
        self.__pyaudio = PyAudio()
        Thread.__init__(self)
        self.start()

    def play(self):
        self.__paused = False

    def seek(self, seconds):
        self.__position = int(seconds * 10)

    def is_playing(self):
        return self.__active and not self.__paused

    def get_position(self):
        return int(self.__position / 10)

    def get_duration(self):
        return int(len(self.__chunks) / 10)

    def pause(self):
        self.__paused = True

    def kill(self):
        self.__active = False

    def __get_stream(self):
        self.__segment = AudioSegment.from_file(self.__path)
        self.__chunks = make_chunks(self.__segment, 100)
        return self.__pyaudio.open(format=self.__pyaudio.get_format_from_width(self.__segment.sample_width),
                                   channels=self.__segment.channels,
                                   rate=self.__segment.frame_rate,
                                   output=True)

    def run(self):
        stream = self.__get_stream()
        while self.__position < len(self.__chunks):
            if not self.__active:
                break
            if not self.__paused:
                # noinspection PyProtectedMember
                data = self.__chunks[self.__position]._data
                self.__position += 1
            else:
                free = stream.get_write_available()
                data = chr(0) * free
            stream.write(data)

        stream.stop_stream()
        self.__pyaudio.terminate()
        if self.__active:
            self.on_terminated()


class Player:
    def __init__(self):
        self.cached_next = None
        self.cached_next_file = None
        self.track = None
        """:type : musiclibrary.Track"""
        self.__queue = []
        self.__stream = None

    def load(self, track):
        self.__queue = []
        if self.__stream:
            self.__stream.kill()
        self.__load(track)

    def clear_queue(self):
        self.__queue = []

    def set_queue(self, queue):
        self.__queue = queue.__reversed__()

        self.cached_next = Stream(self.__queue[-1].file, self.next_track) if \
            (len(self.__queue) and self.__queue[-1].file!=self.cached_next_file) else None
        self.cached_next_file = \
            self.__queue[-1].file if (len(self.__queue) and self.__queue[-1].file != self.cached_next_file) else None

    def __load(self, track):
        if self.cached_next:
            self.cached_next.kill()
            self.cached_next = None
            self.cached_next_file = None
        self.kill_stream()
        self.track = track
        self.__stream = Stream(self.track.file, self.next_track)

    def add_to_queue(self, track):
        self.__queue.insert(0, track)
        if len(self.__queue) and self.__queue[-1].file!=self.cached_next_file:
            self.cached_next = Stream(self.__queue[-1].file, self.next_track)
            self.cached_next_file = self.__queue[-1].file

    def get_queue(self):
        return list(self.__queue.__reversed__())

    @staticmethod
    def set_volume(value):
        mixer.setvolume(value)

    @staticmethod
    def get_volume():
        return mixer.getvolume()

    def get_position(self):
        if self.__stream:
            return self.__stream.get_position()
        else:
            return 0

    def get_duration(self):
        if self.__stream:
            return self.__stream.get_duration()
        else:
            return 0

    def is_playing(self):
        return self.__stream and self.__stream.is_playing()

    def get_json_status(self):
        vol = self.get_volume()
        data = {"vol_left": vol[0],
                "vol_right": vol[0] if len(vol) == 1 else vol[1],
                "status": "playing" if self.is_playing() else "paused"}
        if self.track:
            data["file"] = self.track.file
            data["position"] = self.get_position()
            data["duration"] = self.get_duration()
            data["artist"] = self.track.artist.name
            data["album"] = self.track.album.name
            data["title"] = self.track.title
        return data

    def pause(self):
        if self.__stream:
            self.__stream.pause()

    def play(self):
        if self.__stream:
            self.__stream.play()

    def stop(self):
        if self.__stream:
            self.__stream.pause()
            self.__stream.seek(0)

    def kill_stream(self):
        if self.__stream:
            self.__stream.kill()

    def seek(self, seconds):
        if self.__stream:
            self.__stream.seek(seconds)

    def next_track(self):
        self.kill_stream()
        if self.__queue:
            if not self.cached_next:
                self.__load(self.__queue.pop())
            else:
                self.__stream = self.cached_next
                self.track = self.__queue.pop()
            self.play()
        else:
            self.track = None
        self.cached_next = Stream(self.__queue[-1].file, self.next_track) if \
            (len(self.__queue) and self.__queue[-1].file != self.cached_next_file) else None
        self.cached_next_file = \
            self.__queue[-1].file if (len(self.__queue) and self.__queue[-1].file != self.cached_next_file) else None

    def prev_track(self):
        self.seek(0)


def get_musiclibrary():
    lib_files = music_library.get_file_list(config.library_path)
    global lib
    lib = music_library.parse_library(lib_files)
    """:type :musiclibrary.MusicLibrary"""
    return lib
