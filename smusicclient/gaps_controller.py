# -*- coding: utf-8 -*-
from functools import wraps
from datetime import datetime, timedelta
import time
import cmus_utils
import config
from threading import Thread
import logging

gap_list = []

STATE_UNLOCKED = 0
STATE_LOCKED = 1


def get_bells_time():
    return (datetime.now() + timedelta(milliseconds=config.clock_correction)).time()


class Gap:
    def __init__(self, beginning, ending):
        self.beginning = beginning
        self.ending = ending

    def is_gap(self):
        return self.beginning <= get_bells_time() <= self.ending


def is_unlocked():
    unlocked = False
    for gap in gap_list:
        if gap.is_gap():
            unlocked = True
    return unlocked


def load_gaps():
    for el in config.gaps:
        gap_list.append(Gap(datetime.strptime(el[0], "%H:%M").time(), datetime.strptime(el[1],"%H:%M").time()))
        logging.info("Załadowano przerwę od {} do {}".format(
            gap_list[gap_list.count(0)-1].beginning, gap_list[gap_list.count(0)-1].ending))


class GapThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.__was_stopped = False

    def run(self):
        last_state = -1
        while not self.__was_stopped:
            unlocked = is_unlocked()
            if unlocked and last_state != STATE_UNLOCKED:
                last_state = STATE_UNLOCKED
                logging.debug("Odblokowano odtwarzacz")
            elif not unlocked and last_state != STATE_LOCKED:
                cmus_utils.player_pause()
                last_state = STATE_LOCKED
                logging.debug("Zablokowano odtwarzacz")
            time.sleep(1)

    def stop(self):
        self.__was_stopped = True

