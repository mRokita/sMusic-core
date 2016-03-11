#!/usr/bin/python2
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(name="sMusicClient",
      version="0.1.2",
      description="Klient sMusic",
      url="https://github.com/mRokita/sMusic-core/",
      author="Michał Rokita & Artur Puzio",
      author_email="mrokita@mrokita.pl & cytadela88@gmail.com",
      packages=["smusicclient"],
      scripts=["sMusicClient"],
      requires=["whoosh"],
      data_files=[('/etc/sMusic', ['client.default.ini']),
                  ('/usr/lib/systemd/system', ['sMusicClient.service'])]
     )
