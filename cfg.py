# -*- coding: utf-8 -*-
from ConfigParser import ConfigParser

THUMBNAILS_NOAA = {
    "norm_thumb": (400, 354),
    "norm_thumb_sm": (200, 177),
    "enh_thumb": (400, 809),
    "enh_thumb_sm": (300, 607)
}


class AsciiColors:
    def __init__(self):
        pass

    HEADER = '\033[95m'
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[97m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    GRAY = '\033[37m'
    UNDERLINE = '\033[4m'


logLineStart = AsciiColors.BOLD + AsciiColors.HEADER + "***>\t" + AsciiColors.ENDC + AsciiColors.OKGREEN
logLineEnd = AsciiColors.ENDC


class MyConfigParser(ConfigParser):
    def getlist(self, section, option):
        value = self.get(section, option)
        return list(filter(None, (x.strip() for x in value.splitlines())))

    def getlistint(self, section, option):
        return [int(x) for x in self.getlist(section, option)]


def get(f):
    config = MyConfigParser()
    config.read(f)
    return config
