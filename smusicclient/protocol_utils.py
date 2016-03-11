# -*- coding: utf-8 -*-
from threading import Thread
import logs
import cmus_utils
import gaps_controller as gaps
import json
import re
from inspect import getargspec
import config
from base64 import b64decode, b64encode
from functools import partial, wraps

PATTERN_MSG = re.compile("([ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789=+/]*?)\n(.+)?", re.DOTALL)


class Binder:
    def __init__(self):
        self.binds = dict()
        self.gaps = None
        self.conn = None
        self.lib = None

    def set_gaps_controller(self, ctl):
        self.gaps = ctl

    def set_connection(self, ctl):
        self.conn = ctl

    def set_library(self, lib):
        self.lib = lib

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
    def __init__(self, conn, binder):
        Thread.__init__(self)
        self.daemon = True
        self.__was_stopped = False
        logs.print_info("Łączenie z serwerem...")
        self.conn = conn
        self.binder = binder
        self.conn.connect((config.server_host, config.server_port))
        logs.print_info("Połączono z serwerem!")

    def run(self):
        logs.print_info("Oczekiwanie na handshake...")
        buff = ""
        msg = self.conn.read()
        while msg and not self.__was_stopped:
            parsed_msg = PATTERN_MSG.findall(msg)
            if len(parsed_msg) == 1 and len(parsed_msg[0]) == 2:
                buff += parsed_msg[0][1]
                esc_string = parsed_msg[0][0]
                data = json.loads(un_escape(esc_string))
                logs.print_debug("RECEIVED: %s" % data)
                if "request" in data:
                    Thread(target=partial(self.binder.handle_message, data, self.conn)).start()
            else:
                buff = ""
            msg = self.conn.read()

    def stop(self):
        self.__was_stopped = True
        self.conn.close()


def escape(msg):
    return b64encode(msg) + "\n"


def un_escape(msg):
    return b64decode(msg)

