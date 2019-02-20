#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""AutoWX

Usage:
  autowx.py update-keps [--config=<cfg>] [--force]
  autowx.py auto [--config=<cfg>] [--force-keps-update]
  autowx.py web [--config=<cfg>]
  autowx.py (-h | --help)
  autowx.py --version

Options:
  -h --help         Show this screen.
  --version         Show version.
  --debug           Log debug.
  --config=<cfg>    Configuration file to use [default: autowx.ini]
"""

from docopt import docopt
import cfg
import keps
import noaa
import web

if __name__ == '__main__':
    arguments = docopt(__doc__, version='AutoWX 1.0')

    config = cfg.get(arguments['--config'])

    print "Using config file: {}".format(arguments['--config'])

    try:
      if arguments['update-keps']:
          keps.update_keps(config, arguments['--force'])
      elif arguments['auto']:
          if arguments['--force-keps-update']:
              keps.update_keps(config, force=True)

          noaa.auto_sat_magic(config, arguments['--config'])
      elif arguments['web']:
          web.static_web_generation(config)
    except KeyboardInterrupt, e:
      print "Exiting."
