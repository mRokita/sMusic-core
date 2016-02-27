# -*- coding: utf-8 -*-
"""
Domyślny config sMusic-core
"""

ssl_validate_cert = False

# Host serwera uruchamiającego core_server
server_host = "localhost"

# Port core_server
server_port = 3484

# Klucz dla RADIO (musi być taki sam jak w configu core_server
server_key = "dafekIWska"

# Przerwy
gaps = [["7:45", "8:15"],
          ["9:00", "9:10"],
          ["9:55", "10:10"]]

# Opóźnienie dzwonka w stosunku do zegara systemoweg, w milisekundach
clock_correction = 0

# Ścieżka do przechowywania logów
log_path = "logs"
