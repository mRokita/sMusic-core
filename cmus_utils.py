# -*- coding: utf-8 -*-
from subprocess import check_output
import re


# TODO: Dodać obsługę kolejki
__doc__ = "Moduł zawierający funkcje kontrolujące CMUSa"

PATTERN_STATUS = re.compile("(?:tag|set)? ?([abcdefghijklmnopqrstuvxyz_]+|duration|file) (.+)", re.DOTALL)


def exec_cmus_command(command):
    return check_output(["cmus-remote", "-C", command])


def get_player_status():
    output = check_output(["cmus-remote", "-Q"]).split("\n")
    status = dict()
    for line in output:
        match = PATTERN_STATUS.findall(line)
        if match:
            status[match[0][0]] = match[0][1]
    return status


def player_pause():
    exec_cmus_command("player-pause")


def player_play():
    exec_cmus_command("player-play")


def player_next():
    exec_cmus_command("player-next")


def player_prev():
    exec_cmus_command("player-prev")


def player_stop():
    exec_cmus_command("player-stop")


def set_vol(vol):
    return exec_cmus_command("vol {0}%".format(vol))
