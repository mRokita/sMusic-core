import json
import ConfigParser

conf = ConfigParser.ConfigParser()
conf.read("config.ini")

ssl_validate_cert = conf.get("Server", "ssl_validate_cert")
server_port = int(conf.get("Server", "port"))
server_host = conf.get("Server", "host")
server_key = conf.get("Server", "key")
gaps = json.loads(conf.get("Gaps", "gaps"))
clock_correction = int(conf.get("Gaps", "clock_correction"))
log_path = conf.get("Logs", "path")