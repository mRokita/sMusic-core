# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division
from threading import Thread
import time
import youtube_dl
from string import join
from mutagen import File
import random
import string
import os
import shutil
import re
import config
import cmus_utils
import logs


class DownloadObject:
    def __init__(self, url, artist="", album="", track=""):
        self.url = url
        self.artist = artist
        self.album = album
        self.track = track
        pass

    def __str__(self):
        return "%s: %s: %s" % (self.artist, self.album, self.track)


class YoutubeDLDownloadThread(Thread):
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
        self.__filename = "not_ready.mp3"
        self.__tmpfilename = ""

    def progress_hook(self, data):
        if data[u"status"] == u"downloading":
            self.__speed = data[u"speed"]
            self.__progress = (data[u'downloaded_bytes'] / data[u'total_bytes']) * 0.99
            self.__eta = data[u'eta']+10
        elif data[u"status"] == u"finished":
            logs.print_debug(data)
            self.__progress = 0.99
            self.__eta = 10
            self.__tmpfilename = data[u'filename']
        elif data[u"status"] == u"error":
            self.success = False
            self.ended = True

    def run(self):
        try:
            ydl_opts = {'quiet': True,
                        'progress_hooks': [self.progress_hook],
                        'format': 'bestaudio/best',
                        'outtmpl': '/tmp/smusic/%(title)s.%(ext)s',
                        'noplaylist': True,
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                        }],
                        }

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
                for i in os.listdir("/tmp/smusic"):
                    if os.path.isfile(os.path.join("/tmp/smusic", i)) and \
                                      i.startswith(join(self.__tmpfilename.split('.')[:-1], '.').split('/')[-1]):
                        self.__filename = "/tmp/smusic/" + i
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

    def downloaded_path(self):
        return self.__filename

    def stop(self):
        self.__was_stopped = True


def safe_filename(name):
    return "".join([c for c in name if re.match(r'\w', c)])


def random_string(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


class DownloadQueueThread(Thread):
    queue = []

    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.__was_stopped = False
        self.downloader = None

    def start_download(self):
        if self.downloader is None:
            try:
                method = self.queue[0].url.split(';')[0]
                url = self.queue[0].url.split(';')[1]
            except IndexError as e:
                logs.print_error("Syntax error in URL: %s" % e)
            if method == "youtube-dl":
                self.downloader = YoutubeDLDownloadThread(url)
                logs.print_debug("Starting download of %s with youtube-dl" % url)
            else:
                logs.print_error("Unknown download method %s" % method)
                return
            self.downloader.start()
        else:
            logs.print_warning("Download thread already exists")

    def run(self):
        while not self.__was_stopped:
            if self.downloader is not None and self.downloader.ended:
                f = File(self.downloader.downloaded_path(), easy=True)
                if not re.search('[a-zA-Z0-9]', self.queue[0].artist):
                    if re.search('[a-zA-Z0-9]', f.get("artist", "")):
                        self.queue[0].artist = f["artist"]
                    else:
                        self.queue[0].artist = "Unknown"
                        f["artist"] = self.queue[0].artist
                else:
                    f["artist"] = self.queue[0].artist
                if not re.search('[a-zA-Z0-9]', self.queue[0].album):
                    if re.search('[a-zA-Z0-9]', f.get("album", "")):
                        self.queue[0].album = f["album"]
                    else:
                        self.queue[0].album = "Unknown"
                        f["album"] = self.queue[0].album
                else:
                    f["album"] = self.queue[0].album
                if not re.search('[a-zA-Z0-9]', self.queue[0].track):
                    if re.search('[a-zA-Z0-9]', f.get("title", "")):
                        self.queue[0].track = f["title"]
                    else:
                        self.queue[0].track = join(self.downloader.downloaded_path().split("/")[-1].split(".")[0:-1], '.')
                        f["title"] = self.queue[0].track
                else:
                    f["title"] = self.queue[0].track
                print f.tags
                f.save()

                target_dir = join([config.download_path,
                                   safe_filename(self.queue[0].artist),
                                   safe_filename(self.queue[0].album)], "/")
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                file_path = target_dir + "/" + safe_filename(self.queue[0].track) + "_" + random_string() + "." + self.downloader.downloaded_path().split(".")[-1]
                shutil.move(self.downloader.downloaded_path(), file_path)

                cmus_utils.add_to_library(file_path)
                del self.queue[0]
                self.downloader = None
                if len(self.queue) > 0:
                    self.start_download()
            time.sleep(1)

    def add_download(self, url, artist="", album="", track=""):
        self.queue.append(DownloadObject(url, artist, album, track))
        logs.print_debug("added new url to download")
        if self.downloader is None:
            self.start_download()

    def get_status(self):
        if self.downloader is not None:
            return {"status": "downloading",
                    "progress": self.downloader.progress(),  # postep w procentach
                    "speed": self.downloader.speed(),  # predkosc w bps
                    "eta": self.downloader.eta(),  # pozostaly czas w sekundach
                    "queue_len": len(self.queue)}
        else:
            return {"status": "idle"}

    def get_queue(self):
        return self.queue

    def remove_current_from_download(self):
        pass

    def remove_element_from_queue(self, num):
        if num == 0:
            self.remove_current_from_download()
        else:
            del self.queue[num]

    def clear_queue(self):
        del self.queue[1:]
        self.remove_current_from_download()

    def stop(self):
        self.__was_stopped = True
        if self.downloader is not None:
            self.downloader.stop()


def init():
    global thread
    thread = DownloadQueueThread()
    thread.start()
