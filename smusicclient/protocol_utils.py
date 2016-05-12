# -*- coding: utf-8 -*-
from threading import Thread
import logs
import json
import re
from inspect import getargspec
import config
from base64 import b64decode, b64encode
from functools import partial, wraps
import datetime
import time
import socket
import ssl

PATTERN_MSG = re.compile("([ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789=+/]*?)\n(.+)?", re.DOTALL)

timeout_time = datetime.timedelta(seconds=30)

class Binder:
    def __init__(self):
        self.binds = dict()
        self.gaps = None
        self.conn = None
        self.lib = None
        self.player = None
        """:type : smusicclient.player.Player"""

    def set_gaps_controller(self, ctl):
        self.gaps = ctl

    def set_connection(self, ctl):
        self.conn = ctl

    def set_library(self, lib):
        self.lib = lib

    def set_player(self, player):
        self.player = player

    def requires_unlocked(self):
        def wrapped(function):
            @wraps(function)
            def decorated(*args, **kwargs):
                if self.gaps.is_unlocked():
                    return function(*args, **kwargs)
                else:
                    return {"request": "error", "type": "locked", "comment": "Sterowanie zablokowane", "cat": "=^..^="}
            return decorated
        return wrapped

    def bind(self):
        def bind(function):
            argspec = getargspec(function)
            args = argspec[0]
            if argspec[-1]:
                req_args = args[:len(argspec[-1]) - 1]
            else:
                req_args = args
            self.binds[function.__name__] = {
                "target": function,
                "reqired_args": req_args,
                "args": args
            }
            return function
        return bind

    def handle_message(self, data, conn):
        target = self.binds[data["request"]]["target"]
        datacpy = dict(data)
        del datacpy["request"]
        if "msgid" in datacpy:
            del datacpy["msgid"]
        ret = target(**datacpy)
        if "msgid" in data:
            ret["msgid"] = data["msgid"]
        logs.print_debug("RETURNING: %s" % ret)
        conn.send(escape(json.dumps(ret)))


class ConnectionThread(Thread):
    def __init__(self, binder):
        Thread.__init__(self)
        self.daemon = True
        self.__was_stopped = False
        logs.print_info("Łączenie z serwerem...")
        self.binder = binder
        self.conn = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        self.binder.set_connection(self.conn)
        self.conn.connect((config.server_host, config.server_port))
        logs.print_info("Połączono z serwerem!")
        self.__is_connected = True
        self.last_seen = datetime.datetime.now()

    def run(self):
        logs.print_info("Oczekiwanie na handshake...")
        msg = self.conn.read()
        Thread(target=self.__pinger).start()
        buff = ""
        while not self.__was_stopped:
            buff += msg
            self.last_seen = datetime.datetime.now()
            if '\n' in msg:
                esc_string = buff[:buff.index('\n')]
                buff = buff[buff.index('\n') + 1:]
                data = json.loads(un_escape(esc_string))
                logs.print_debug("RECEIVED: %s" % data)
                if "request" in data:
                    Thread(target=partial(self.binder.handle_message, data, self.conn)).start()
            while not self.__is_connected:
                pass
            try:
                msg = self.conn.read()
            except socket.error as e:
                logs.print_warning("socket.error while waiting for server request: %s" % e)
                self.__is_connected = False
            if not msg:
                logs.print_warning("Serwer zamknal polaczenie")
                self.__is_connected = False

    def stop(self):
        self.__was_stopped = True
        self.conn.close()

    def reconnect(self):
        logs.print_info("Proba ponownego nawiazania polaczenia")
        try:
            self.conn.close()
        except Exception as e:
            logs.print_debug("exception while closing connection in reconnecting: %s" % e)
        self.conn = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        self.binder.set_connection(self.conn)
        try:
            self.conn.settimeout(10)
            self.conn.connect((config.server_host, config.server_port))
            self.conn.settimeout(None)
            self.__is_connected = True
            self.last_seen = datetime.datetime.now()
            logs.print_info("Nawiazano polaczenie ponownie")
        except socket.error as e:
            logs.print_warning("exception while trying to reconnewct: %s " % e)

    def __pinger(self):
        while not self.__was_stopped:
            if datetime.datetime.now() - self.last_seen > timeout_time:
                logs.print_debug("Serwer przekroczyl czas oczekiwania na odpowiedz")
                self.reconnect()
            # TODO dodać wysyłanie pingów
            if not self.__is_connected:
                self.reconnect()
            time.sleep(1)


def escape(msg):
    return b64encode(msg) + "\n"


def un_escape(msg):
    return b64decode(msg)
