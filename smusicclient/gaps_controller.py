# -*- coding: utf-8 -*-
import logging
import time
from datetime import datetime, timedelta
from threading import Thread

import config
from smusicclient import logs

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
        gap_list.append(Gap(datetime.strptime(el[0], "%H:%M").time(), datetime.strptime(el[1], "%H:%M").time()))
        logs.print_info("Załadowano przerwę od {} do {}".format(
            gap_list[gap_list.count(0) - 1].beginning, gap_list[gap_list.count(0) - 1].ending))


class GapThread(Thread):
    def __init__(self, player):
        Thread.__init__(self)
        self.player = player
        self.daemon = True
        self.__was_stopped = False

    def run(self):
        last_state = -1
        while not self.__was_stopped:
            unlocked = is_unlocked()
            if unlocked and last_state != STATE_UNLOCKED:
                last_state = STATE_UNLOCKED
                logs.print_info("Odblokowano odtwarzacz")
            elif not unlocked and last_state != STATE_LOCKED:
                self.player.pause()
                last_state = STATE_LOCKED
                logs.print_info("Zablokowano odtwarzacz")
            time.sleep(1)

    def stop(self):
        self.__was_stopped = True
