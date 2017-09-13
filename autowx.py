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

if __name__ == '__main__':
    arguments = docopt(__doc__, version='AutoWX 1.0')
    print(arguments)

    config = cfg.get(arguments['--config'])

    if arguments['update-keps']:
        keps.update_keps(config, arguments['--force'])
