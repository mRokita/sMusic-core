"""
Bardzo minimalny testowy klient TCP
"""
import config
import socket
import ssl
import cmus_utils
import re
import json
from base64 import b64encode, b64decode
from inspect import getargspec

binds = {}
PATTERN_MSG = re.compile("([ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789=+/]*?)\n(.+)?", re.DOTALL)


def escape(msg):
    return b64encode(msg)+"\n"


def un_escape(msg):
    return b64decode(msg)


def bind(function):
    argspec = getargspec(function)
    args = argspec[0]
    if argspec[-1]:
        req_args = args[:len(argspec[-1])-1]
    else:
        req_args = args
    binds[function.__name__] = {
        "target": function,
        "reqired_args": req_args,
        "args": args
    }
    return function


@bind
def type():
    return {"request": "ok", "type": "radio", "key": config.server_key}


@bind
def pause():
    cmus_utils.player_pause()
    return {"request": "ok", "status": cmus_utils.get_player_status()}


@bind
def play():
    cmus_utils.player_play()
    return {"request": "ok", "status": cmus_utils.get_player_status()}


@bind
def play_next():
    cmus_utils.player_next()
    return {"request": "ok", "status": cmus_utils.get_player_status()}


if __name__ == "__main__":
    print "Analizowanie biblioteki..."
    library = cmus_utils.get_current_library()
    print "\rZakończono analizowanie biblioteki."
    conn = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    conn.connect((config.server_host, config.server_port))
    msg = conn.read()
    buff = ""
    while msg:
        parsed_msg = PATTERN_MSG.findall(msg)
        if len(parsed_msg) == 1 and len(parsed_msg[0]) == 2:
            buff += parsed_msg[0][1]
            esc_string = parsed_msg[0][0]
            data = json.loads(un_escape(esc_string))
            if "request" in data:
                print "RECEIVED: %s" % data
                target = binds[data["request"]]["target"]
                datacpy = dict(data)
                del datacpy["request"]
                if "msgid" in datacpy:
                    del datacpy["msgid"]
                ret = target(**datacpy)
                if "msgid" in data:
                    ret["msgid"] = data["msgid"]

                print "RETURNING: %s" % ret
                conn.send(escape(json.dumps(ret)))
        else:
            buff = ""
        msg = conn.read()
