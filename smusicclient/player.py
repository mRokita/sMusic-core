# -*- coding: utf-8 -*-
from pydub import AudioSegment
from pydub.utils import make_chunks
from pyaudio import PyAudio
from threading import Thread
import musiclibrary
from alsaaudio import Mixer
import config
mixer = Mixer(cardindex=config.cardindex)


class Stream(Thread):
    def __init__(self, f, on_terminated):
        self.__active = True
        self.__paused = True
        self.__segment = AudioSegment.from_file(f)
        self.on_terminated = on_terminated
        self.__position = 0
        self.__chunks = make_chunks(self.__segment, 100)
        self.__pyaudio = PyAudio()
        Thread.__init__(self)
        self.start()

    def play(self):
        self.__paused = False

    def seek(self, seconds):
        self.__position = int(seconds*10)

    def is_playing(self):
        return self.__active and not self.__paused

    def get_position(self):
        return int(self.__position/10)

    def get_duration(self):
        return int(len(self.__chunks)/10)

    def pause(self):
        self.__paused = True

    def kill(self):
        self.__active = False

    def __get_stream(self):
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
                data = self.__chunks[self.__position]._data
                self.__position += 1
            else:
                free = stream.get_write_available()
                data = chr(0)*free
            stream.write(data)

        stream.stop_stream()
        self.__pyaudio.terminate()
        if self.__position < len(self.__chunks) and self.__active:
            self.on_terminated()


class Player:
    def __init__(self):
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

    def __load(self, track):
        self.stop()
        self.track = track
        self.__stream = Stream(self.track.file, self.next_track)

    def add_to_queue(self, track):
        self.__queue.insert(0, track)

    def get_queue(self):
        return list(self.__queue.__reversed__())

    def clear_queue(self):
        self.__queue = []

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
            self.__load(self.__queue.pop())
            self.play()
        else:
            self.track = None

    def prev_track(self):
        self.seek(0)

def get_musiclibrary():
    lib_files = musiclibrary.get_file_list(config.library_path)
    global lib
    lib = musiclibrary.parse_library(lib_files)
    """:type :musiclibrary.MusicLibrary"""
    return lib