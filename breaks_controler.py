from functools import wraps
from datetime import datetime, timedelta
import time
import cmus_utils
import config


przerwy = []


def get_dzwonki_time():
    return (datetime.now() + timedelta(milliseconds=config.clock_correction)).time();


class Przerwa:
    def __init__(self, poczatek, koniec):
        self.poczatek = poczatek
        self.koniec = koniec

    def is_przerwa(self):
        return self.poczatek <= get_dzwonki_time() <= self.koniec


def is_unlocked():
    unlocked = False
    for przerwa in przerwy:
        if przerwa.is_przerwa():
            unlocked = True
    return unlocked


def load_breaks():
    for el in config.breaks:
        przerwy.append(Przerwa(datetime.strptime(el[0], "%H:%M").time(), datetime.strptime(el[1],"%H:%M").time()))
        print "zaladowano przerwe od: ", przerwy[przerwy.count(0)-1].poczatek, "do: ", przerwy[przerwy.count(0)-1].koniec


def breaks_controller():
    paused = 0
    was_playing = cmus_utils.is_playing()
    while True:
        if is_unlocked():
            if paused > 0:
                paused = 0
                print "odblokowywanie"
                if was_playing:
                    print "wznawianie odtwarzania"
                    cmus_utils.player_play()
        else:
            if paused < 30:
                if paused == 0:
                    was_playing = cmus_utils.is_playing()
                    print "blokowanie, czy trwalo odtwarzanie: ", was_playing
                paused += 1
                print "b..."
                cmus_utils.player_pause()
        time.sleep(1)


def requires_unlocked(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if is_unlocked():
            return f(*args, **kwargs)
        else:
            return {"request": "error", "type": "locked", "comment": "Sterowanie zablokowane", "cat": "=^..^="}
    return decorated