#!/usr/bin/python2
# -*- coding: utf-8 -*-

from distutils.core import setup
from smusicclient import __version__

setup(name="sMusicClient",
      version=__version__,
      description="Klient sMusic",
      url="https://github.com/mRokita/sMusic-core/",
      download_url="https://github.com/mRokita/sMusic-core/tarball/%s" % __version__,
      keywords=["smusic", "core", "staszic", "music"],
      author="Michał Rokita & Artur Puzio",
      author_email="mrokita@mrokita.pl & cytadela88@gmail.com",
      packages=["smusicclient"],
      scripts=["sMusicClient"],
      requires=["whoosh"],
      data_files=[('/etc/sMusic', ['client.default.ini']),
                  ('/usr/lib/systemd/system', ['sMusicClient.service'])]
      )
