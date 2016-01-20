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
    print argspec
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
def print_to_console(text):
    print text


if __name__ == "__main__":
    conn = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    conn.connect((config.server_host, config.server_port))
    msg = conn.read()
    buff = ""
    while msg:
        parsed_msg = PATTERN_MSG.findall(msg)
        print parsed_msg
        if len(parsed_msg)==1 and len(parsed_msg[0]) == 2:
            buff = parsed_msg[0][1]
            esc_string = parsed_msg[0][0]
            try:
                data = json.loads(un_escape(esc_string))
                print data
                target = binds[data["target"]]["target"]
                del data["target"]
                target(**data)
            except ValueError:
                pass

        else:
            buff = ""
        msg = conn.read()
