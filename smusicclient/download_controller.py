# -*- coding: utf-8 -*-
from threading import Thread
from datetime import datetime, timedelta
import time
import logging
import config
import cmus_utils


class DownloadObject:
    def __init__(self, uri, artist="", album="", track=""):
        self.uri = uri
        self.artist = artist
        self.album = album
        self.track = track
        pass

    def __str__(self):
        return "%s: %s: %s" % (self.artist, self.album, self.track)


class DownloadQueueThread(Thread):
    queue = []
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.__was_stopped = False

    def run(self):
        while not self.__was_stopped:
            time.sleep(1)

    def add_download(self, uri, artist="", album="", track=""):
        self.queue.append(DownloadObject(uri, artist, album, track))
        # TODO: if not downloading: start downloading

    def get_status(self):
        return {"progress": 10,  # postep w procentach
                "speed": 100000,  # predkosc w bps
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


def init():
    global thread
    thread = DownloadQueueThread()
    thread.start()