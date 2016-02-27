import json
import ConfigParser
import os.path

conf = ConfigParser.ConfigParser()
config_paths = ["client.ini", "/etc/sMusic/client.ini", "/etc/sMusic/client.default.ini", "client.default.ini"]

found_config = False
for path in config_paths:
    if os.path.isfile(path):
        print "using config from: " + path
        conf.read(path)
        found_config = True
        break

if not found_config:
    print "ERROR! NO CONFIG FILE FOUND!!!"
    print "checked locations: " + config_paths

ssl_validate_cert = conf.get("Server", "ssl_validate_cert")
server_port = int(conf.get("Server", "port"))
server_host = conf.get("Server", "host")
server_key = conf.get("Server", "key")
gaps = json.loads(conf.get("Gaps", "gaps"))
clock_correction = int(conf.get("Gaps", "clock_correction"))
log_path = conf.get("Logs", "path")
