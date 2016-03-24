# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division
from threading import Thread
import time
import youtube_dl
import config
import cmus_utils
import logs


class DownloadObject:
    def __init__(self, uri, artist="", album="", track=""):
        self.uri = uri
        self.artist = artist
        self.album = album
        self.track = track
        pass

    def __str__(self):
        return "%s: %s: %s" % (self.artist, self.album, self.track)


class YoutubeDownloadThread(Thread):
    def __init__(self, url):
        Thread.__init__(self)
        self.daemon = True
        self.__was_stopped = False
        self.ended = False
        self.success = False
        self.url = url
        self.__speed = 0  # in bytes per second
        self.__progress = 0  # float in range 0 to 1
        self.__eta = 0  # in seconds

    def progress_hook(self, data):
        if data[u"status"] == u"downloading":
            self.__speed = data[u"speed"]
            self.__progress = (data[u'downloaded_bytes'] / data[u'total_bytes']) * 0.99
            self.__eta = data[u'eta']+10
        elif data[u"status"] == u"finished":
            self.__progress = 0.99
            self.__eta = 10
        elif data[u"status"] == u"error":
            self.success = False
            self.ended = True

    def run(self):
        try:
            ydl_opts = {'quiet': True,
                        'progress_hooks': [self.progress_hook],
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                        }

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
                self.success = True
                self.__eta = 0
                self.__progress = 1
        except Exception as e:
            self.success = False
            self.ended = True
            logs.print_error(e)  # TODO: do something more proper with the exception
        self.ended = True

    def speed(self):
        return self.__speed

    def progress(self):
        return self.__progress

    def eta(self):
        return self.__eta

    def stop(self):
        self.__was_stopped = True


class DownloadQueueThread(Thread):
    queue = []

    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.__was_stopped = False
        self.downloader = None

    def start_download(self):
        if self.downloader is None:
            method = self.queue[0].uri.split(';')[0]
            url = self.queue[0].uri.split(';')[1]
            if method == "youtube-dl":
                self.downloader = YoutubeDownloadThread(url)
                logs.print_debug("Starting download of %s with youtube-dl" % url)
            else:
                logs.print_error("Unknown download method %s" % method)
            self.downloader.start()
        else:
            logs.print_warning("Download thread already exists")

    def run(self):
        while not self.__was_stopped:
            if self.downloader is not None and self.downloader.ended:
                del self.queue[0]
                self.downloader = None
                if len(self.queue) > 0:
                    self.start_download()
            time.sleep(1)

    def add_download(self, uri, artist="", album="", track=""):
        self.queue.append(DownloadObject(uri, artist, album, track))
        logs.print_debug("added new url to download")
        if self.downloader is None:
            self.start_download()

    def get_status(self):
        if self.downloader is not None:
            return {"status": "downloading",
                    "progress": self.downloader.progress(),  # postep w procentach
                    "speed": self.downloader.speed(),  # predkosc w bps
                    "eta": self.downloader.eta(),
                    "queue_len": len(self.queue)}
        else:
            return {"status": "idle",
                    "progress": 0,
                    "speed": 0,
                    "eta": 0,
                    "queue_len": len(self.queue)}

    def get_queue(self):
        return self.queue

    def remove_current_from_download(self):
        pass

    def remove_element_from_queue(self, num):
        if num == 0:
            self.remove_current_from_download()
        else:
            del self.queue[num]

    def stop(self):
        self.__was_stopped = True
        if self.downloader is not None:
            self.downloader.stop()


def init():
    global thread
    thread = DownloadQueueThread()
    thread.start()
