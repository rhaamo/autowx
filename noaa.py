#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import datetime
from time import strftime
import pypredict
import subprocess
import os
import re
import sys
import cfg
import web
import tle_draw


#############################
#                          ##
#     Here be dragons.     ##
#                          ##
#############################

class Logger(object):
    def __init__(self, filename="Default.log"):
        self.terminal = sys.stdout
        self.log = open(filename, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)


def log_cmdline(what, cmdline, debug=False):
    if debug:
        print cfg.logLineStart + what + ": '" + " ".join(cmdline) + "'" + cfg.logLineEnd
        print cmdline


# Execution loop declaration
def run_for_duration(cmdline, sleep_for):
    try:
        child = subprocess.Popen(cmdline)
        time.sleep(sleep_for)
        child.terminate()
    except OSError as e:
        print "OS Error during command: " + " ".join(cmdline)
        print "OS Error: " + e.strerror


# FM Recorder definition
def record_fm(config, frequency, filename, sleep_for, sat_name):
    print cfg.AsciiColors.GRAY
    xf_no_space = sat_name.replace(" ", "")
    output_file = os.path.join(config.get('DIRS', 'rec'), "{}-{}.raw".format(xf_no_space, filename))

    cmdline = ['/usr/bin/rtl_fm',
               '-f', str(frequency),
               '-s', config.get('SDR', 'sample'),
               '-g', config.get('SDR', 'gain'),
               '-F', '9',
               '-l', '0',
               '-t', '900',
               '-A', 'fast',
               '-E', 'offset',
               # '-E','pad',
               '-p', config.get('SDR', 'shift'),
               '-d', config.get('SDR', 'index'),
               output_file]

    log_cmdline("RECORD FM", cmdline, config.getboolean("LOG", 'debug'))

    run_for_duration(cmdline, sleep_for)


def record_qpsk(config, cfg_file, sleep_for):
    print cfg.AsciiColors.GRAY
    cmdline = [os.path.join(config.get('DIRS', 'system'), 'meteor_qpsk.py'),
               cfg_file]
    run_for_duration(cmdline, sleep_for)


# Status builder. Crazy shit. These are only examples, do what you want :)
def write_status(config, frequency, aos_time, los_time, los_time_unix, record_time, xf_name, max_elev, status):
    aos_time_str = strftime('%H:%M:%S', time.localtime(aos_time))
    stat_file = open(config.get('DIRS', 'status'), 'w+')
    if status == 'RECORDING':
        stat_file.write("RECEIVING;yes;" + str(xf_name) + " QRG" + str(frequency) +
                        ' AOS@' + str(aos_time_str) + ' LOS@' + str(los_time) +
                        ' REC@' + str(record_time) + 's. max el.@' + str(max_elev) + '\xb0' + ';' +
                        str(xf_name) + '-' + strftime('%Y%m%d-%H%M', time.localtime(aos_time)))

    elif status == 'DECODING':
        stat_file.write('RECEIVING;no;Decoding ' + str(xf_name) + " QRG" + str(frequency) + ';' + str(xf_name) +
                        '-' + strftime('%Y%m%d-%H%M', time.localtime(aos_time)))

    elif status == 'WAITING':
        stat_file.write('RECEIVING;no;' + str(xf_name) + " QRG" + str(frequency) +
                        ' (AOS@' + str(aos_time_str) + ') @' + str(max_elev) + "\xb0 elev. max" + ';' +
                        str(xf_name) + '-' + strftime('%Y%m%d-%H%M', time.localtime(los_time_unix)))

    elif status == 'TOOLOW':
        stat_file.write('RECEIVING;no;' + str(xf_name) + " QRG" + str(frequency) +
                        ' (AOS@' + str(aos_time_str) + ') too low (' + str(max_elev) + '\xb0), waiting ' +
                        str(record_time) + 's.')

    stat_file.close()


# Transcoding module
def transcode(config, filename, sat_name):
    xf_no_space = sat_name.replace(" ", "")
    print cfg.logLineStart + 'Transcoding...' + cfg.AsciiColors.YELLOW
    in_file = os.path.join(config.get('DIRS', 'rec'), "{}-{}.raw".format(xf_no_space, filename))
    out_file = os.path.join(config.get('DIRS', 'rec'), "{}-{}.wav".format(xf_no_space, filename))

    cmdlinesox = ['sox',
                  '-t', 'raw',
                  '-r', config.get('SDR', 'sample'),
                  '-es',
                  '-b', '16',
                  '-c', '1',
                  '-V1',
                  in_file,
                  out_file,
                  'rate',
                  config.get('SDR', 'wavrate')]

    log_cmdline("SOX", cmdlinesox, config.getboolean("LOG", 'debug'))

    subprocess.call(cmdlinesox)
    cmdlinetouch = ['touch',
                    '-r',
                    in_file,
                    out_file]

    log_cmdline('SOX TOUCH', cmdlinetouch, config.getboolean("LOG", 'debug'))

    subprocess.call(cmdlinetouch)
    if config.getboolean('PROCESSING', 'removeRAW'):
        print cfg.logLineStart + cfg.AsciiColors.ENDC + cfg.AsciiColors.RED + 'Removing RAW data' + cfg.logLineEnd
        os.remove(in_file)


def create_overlay(config, filename, aos_time, sat_name, record_len):
    print cfg.logLineStart + 'Creating Map Overlay...' + cfg.logLineEnd
    aos_time_o = int(aos_time) + int('1')
    rec_len_c = int(record_len)
    # recLenC='2'
    mapfname = os.path.join(config.get('DIRS', 'map'), filename)
    cmdline = ['wxmap',
               '-T', sat_name,
               '-G', config.get('DIRS', 'tle'),
               '-H', config.get('DIRS', 'tleFile'),
               '-M', '0',
               '-o',
               '-A', '0',
               '-O', str(rec_len_c),
               '-L', config.get('QTH', 'lat') + '/' + config.get('QTH', 'lon') + '/' + config.get('QTH', 'alt'),
               str(aos_time_o), mapfname + '-map.png']
    overlay_log = open(mapfname + '-map.png.txt', "w+")

    log_cmdline('CREATE OVRLAY WXMAP', cmdline, config.getboolean("LOG", 'debug'))

    subprocess.call(cmdline, stderr=overlay_log, stdout=overlay_log)
    overlay_log.close()

    # Generate thumbnail for overlay
    thumb_dst = os.path.join(config.get('DIRS', 'map'), ".thumb_" + filename + "-map.png")
    thumb_dst_sm = os.path.join(config.get('DIRS', 'map'), ".thumb_sm_" + filename + "-map.png")

    web.generate_thumbnail(mapfname + '-map.png', thumb_dst, cfg.THUMBNAILS_NOAA['enh_thumb'])
    web.generate_thumbnail(mapfname + '-map.png', thumb_dst_sm, cfg.THUMBNAILS_NOAA['enh_thumb_sm'])


def decode_qpsk(config):
    # TODO write config for decode_meteor.sh
    subprocess.Popen(os.path.join(config.get('DIRS', 'system'), 'decode_meteor.sh'))


def decode(config, filename, aos_time, sat_name, max_elev, record_len, wxtoimg_cfg):
    xf_no_space = sat_name.replace(" ", "")
    sat_timestamp = int(filename)
    file_name_c = datetime.datetime.utcfromtimestamp(sat_timestamp).strftime('%Y%m%d-%H%M')

    in_wav = os.path.join(config.get('DIRS', 'rec'), "{}-{}.wav".format(xf_no_space, filename))
    wxtoimg_bin = os.path.join(config.get('DIRS', 'wxInstall'), "wxtoimg")

    if config.getboolean('PROCESSING', 'wxAddOverlay'):
        print cfg.logLineStart + cfg.AsciiColors.OKBLUE + 'Creating overlay map' + cfg.logLineEnd
        create_overlay(config, filename, aos_time, sat_name, record_len)
        print cfg.logLineStart + 'Creating basic image with overlay map' + cfg.logLineEnd
        img_txt = os.path.join(config.get('DIRS', 'img'), sat_name, "{}-normal-map.jpg.txt".format(file_name_c))
        map_txt = os.path.join(config.get('DIRS', 'map'), "{}-map.png.txt".format(filename))
        out_img = os.path.join(config.get('DIRS', 'img'), sat_name, "{}-normal-map.jpg".format(file_name_c))
        scp_img_txt = os.path.join(config.get('SCP', 'dir'), "/",
                                   sat_name.replace(" ", "\ "), "{}-normal-map.jpg.txt".format(file_name_c))
        scp_img = os.path.join(config.get('SCP', 'dir'), "/",
                               sat_name.replace(" ", "\ "), "{}-normal-map.jpg".format(file_name_c))

        m = open(img_txt, "w+")
        m.write('\nSAT: ' + str(xf_no_space) + ', Elevation max: ' + str(max_elev) + ', Date: ' + str(filename) + '\n')

        for psikus in open(map_txt, "r").readlines():
            res = psikus.replace("\n", " \n")
            m.write(res)

        cmdline = [config.get('DIRS', 'wxInstall') + '/wxtoimg',
                   wxtoimg_cfg['wxQuietOpt'],
                   wxtoimg_cfg['wxAddText'],
                   '-A', '-o', '-R1',
                   '-t', 'NOAA',
                   '-Q ' + config.get('PROCESSING', 'wxJPEGQuality'),
                   in_wav,
                   out_img]
        log_cmdline("DECODE WXTOIMG NORMALMAP", cmdline, config.getboolean("LOG", 'debug'))
        subprocess.call(cmdline, stderr=m, stdout=m)
        m.close()

        # Generate thumbnails for normal map
        thumb_norm_dst = os.path.join(config.get('DIRS', 'img'), sat_name,
                                      ".thumb_{}-normal-map.jpg".format(file_name_c))
        thumb_norm_dst_sm = os.path.join(config.get('DIRS', 'img'), sat_name,
                                         ".thumb_sm_{}-normal-map.jpg".format(file_name_c))

        web.generate_thumbnail(out_img, thumb_norm_dst, cfg.THUMBNAILS_NOAA['norm_thumb'])
        web.generate_thumbnail(out_img, thumb_norm_dst_sm, cfg.THUMBNAILS_NOAA['norm_thumb_sm'])

        # Maybe use a default better than None...
        channel_a, channel_b = None, None

        for line in open(img_txt, "r").readlines():
            res = line.replace("\n", "")
            res2 = re.sub(r"(\d)", r"\033[96m\1\033[94m", res)
            print cfg.logLineStart + cfg.AsciiColors.OKBLUE + res2 + cfg.logLineEnd

            if "Channel A" in res:
                chan1 = res.rstrip().replace('(', ':').split(':')
                channel_a = chan1[1].strip().rstrip()[:1]
            if "Channel B" in res:
                chan1 = res.rstrip().replace('(', ':').split(':')
                channel_b = chan1[1].strip().rstrip()[:1]

        # Copy logs
        if config.getboolean('SCP', 'log'):
            print cfg.logLineStart + "Sending flight and decode logs..." + cfg.AsciiColors.YELLOW
            cmdline_scp_log = [config.get("SCP", "bin"),
                               img_txt,
                               config.get('SCP', 'user') + '@' + config.get('SCP', 'host') + ':' +
                               scp_img_txt]
            log_cmdline("SCP LOG", cmdline_scp_log, config.getboolean("LOG", 'debug'))
            subprocess.call(cmdline_scp_log)

        if config.getboolean('SCP', 'img'):
            print cfg.logLineStart + "Sending base image with map: " + cfg.AsciiColors.YELLOW
            cmdline_scp_img = [config.get("SCP", "bin"),
                               out_img,
                               config.get('SCP', 'user') + '@' + config.get('SCP', 'host') + ':' +
                               scp_img]
            log_cmdline("SCP IMG", cmdline_scp_img, config.getboolean("LOG", 'debug'))
            subprocess.call(cmdline_scp_img)
            print cfg.logLineStart + "Sending OK, go on..." + cfg.logLineEnd

        # NEW
        if config.getboolean('PROCESSING', 'wxEnhCreate'):
            print "Channel A:" + channel_a + ", Channel B:" + channel_b
            for enhancements in config.getlist('PROCESSING', 'wxEnhList'):
                print cfg.logLineStart + 'Creating ' + enhancements + ' enhancement image' + cfg.logLineEnd
                enhancements_log_file = os.path.join(config.get('DIRS', 'img'),
                                                     sat_name,
                                                     "{}-{}-map.jpg.txt".format(file_name_c, enhancements))
                enhancements_log = open(enhancements_log_file, "w+")
                enhancements_log.write(
                    '\nEnhancement: ' + enhancements + ', SAT: ' + str(xf_no_space) + ', Elevation max: ' + str(
                        max_elev) + ', Date: ' + str(filename) + '\n')

                enhancements_out_map = os.path.join(config.get('DIRS', 'img'),
                                                    sat_name,
                                                    "{}-{}-map.jpg".format(file_name_c, enhancements))
                wxtoimg_map = os.path.join(config.get('DIRS', 'map'), "{}-map.png".format(filename))

                scp_img_txt_enh = os.path.join(config.get('SCP', 'dir'), "/",
                                               sat_name.replace(" ", "\ "),
                                               "{}-{}-map.jpg.txt".format(file_name_c, enhancements))
                scp_img_enh = os.path.join(config.get('SCP', 'dir'), "/",
                                           sat_name.replace(" ", "\ "),
                                           "{}-{}-map.jpg".format(file_name_c, enhancements))

                if enhancements in ('HVCT', 'HVC'):
                    if channel_a in "1" and channel_b in "2":
                        print "1 i 2"
                        cmdline_enhancements = [wxtoimg_bin, wxtoimg_cfg['wxQuietOpt'], wxtoimg_cfg['wxDecodeOpt'],
                                                wxtoimg_cfg['wxAddText'], '-A', '-K0', '-o', '-c', '-R1',
                                                '-Q ' + config.get('PROCESSING', 'wxJPEGQuality'), '-e', enhancements,
                                                '-m',
                                                wxtoimg_map + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetX') + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetY'),
                                                in_wav,
                                                enhancements_out_map]
                    elif channel_a in "1" and channel_b in "1":
                        print "1 i 1 "
                        cmdline_enhancements = [wxtoimg_bin, wxtoimg_cfg['wxQuietOpt'], wxtoimg_cfg['wxDecodeOpt'],
                                                wxtoimg_cfg['wxAddText'], '-A', '-K0', '-o', '-c', '-R1',
                                                '-Q ' + config.get('PROCESSING', 'wxJPEGQuality'), '-e', enhancements,
                                                '-m',
                                                wxtoimg_map + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetX') + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetY'),
                                                in_wav,
                                                enhancements_out_map]
                    elif channel_a in "1" and channel_b in "4":
                        print "1 i 4 "
                        cmdline_enhancements = [wxtoimg_bin, wxtoimg_cfg['wxQuietOpt'], wxtoimg_cfg['wxDecodeOpt'],
                                                wxtoimg_cfg['wxAddText'], '-A', '-K0', '-o', '-c', '-R1',
                                                '-Q ' + config.get('PROCESSING', 'wxJPEGQuality'), '-e', enhancements,
                                                '-m',
                                                wxtoimg_map + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetX') + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetY'),
                                                in_wav,
                                                enhancements_out_map]
                    elif channel_a in "1" and channel_b in "3":
                        print "1 i 3"
                        cmdline_enhancements = [wxtoimg_bin, wxtoimg_cfg['wxQuietOpt'], wxtoimg_cfg['wxDecodeOpt'],
                                                wxtoimg_cfg['wxAddText'], '-A', '-K3', '-o', '-c', '-R1',
                                                '-Q ' + config.get('PROCESSING', 'wxJPEGQuality'), '-e', enhancements,
                                                '-m',
                                                wxtoimg_map + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetX') + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetY'),
                                                in_wav,
                                                enhancements_out_map]
                    elif channel_a in "2" and channel_b in "4":
                        print "2 i 4"
                        cmdline_enhancements = [wxtoimg_bin, wxtoimg_cfg['wxQuietOpt'], wxtoimg_cfg['wxDecodeOpt'],
                                                wxtoimg_cfg['wxAddText'], '-A', '-K1', '-o', '-c', '-R1',
                                                '-Q ' + config.get('PROCESSING', 'wxJPEGQuality'), '-e', enhancements,
                                                '-m',
                                                wxtoimg_map + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetX') + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetY'),
                                                in_wav,
                                                enhancements_out_map]
                    elif channel_a in "3" and channel_b in "4":
                        print "3 i 4"
                        cmdline_enhancements = [wxtoimg_bin, wxtoimg_cfg['wxQuietOpt'], wxtoimg_cfg['wxDecodeOpt'],
                                                wxtoimg_cfg['wxAddText'], '-A', '-K4', '-o', '-c', '-R1',
                                                '-Q ' + config.get('PROCESSING', 'wxJPEGQuality'), '-e', enhancements,
                                                '-m',
                                                wxtoimg_map + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetX') + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetY'),
                                                in_wav,
                                                enhancements_out_map]
                    else:
                        print "Channel Unknown"
                        cmdline_enhancements = [wxtoimg_bin, wxtoimg_cfg['wxQuietOpt'], wxtoimg_cfg['wxDecodeOpt'],
                                                wxtoimg_cfg['wxAddText'], '-A', '-K1', '-o', '-c', '-R1',
                                                '-Q ' + config.get('PROCESSING', 'wxJPEGQuality'), '-e', enhancements,
                                                '-m',
                                                wxtoimg_map + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetX') + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetY'),
                                                in_wav,
                                                enhancements_out_map]
                if enhancements == 'MSA':
                    if channel_a in ("1", "2") and channel_b in "4":
                        cmdline_enhancements = [wxtoimg_bin, wxtoimg_cfg['wxQuietOpt'], wxtoimg_cfg['wxDecodeOpt'],
                                                wxtoimg_cfg['wxAddText'], '-A', '-o', '-c', '-R1',
                                                '-Q ' + config.get('PROCESSING', 'wxJPEGQuality'), '-e', enhancements,
                                                '-m',
                                                wxtoimg_map + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetX') + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetY'),
                                                in_wav,
                                                enhancements_out_map]
                    else:
                        cmdline_enhancements = [wxtoimg_bin, wxtoimg_cfg['wxQuietOpt'], wxtoimg_cfg['wxDecodeOpt'],
                                                wxtoimg_cfg['wxAddText'], '-A', '-o', '-c', '-R1',
                                                '-Q ' + config.get('PROCESSING', 'wxJPEGQuality'), '-eNO', '-m',
                                                wxtoimg_map + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetX') + ',' +
                                                config.get('PROCESSING', 'wxOverlayOffsetY'),
                                                in_wav,
                                                enhancements_out_map]
                else:
                    cmdline_enhancements = [wxtoimg_bin, wxtoimg_cfg['wxQuietOpt'], wxtoimg_cfg['wxDecodeOpt'],
                                            wxtoimg_cfg['wxAddText'], '-A', '-o', '-c', '-R1',
                                            '-Q ' + config.get('PROCESSING', 'wxJPEGQuality'), '-e', enhancements, '-m',
                                            wxtoimg_map + ',' +
                                            config.get('PROCESSING', 'wxOverlayOffsetX') + ',' +
                                            config.get('PROCESSING', 'wxOverlayOffsetY'),
                                            in_wav,
                                            enhancements_out_map]
                log_cmdline("ENHANCEMENTS WXTOIMG", cmdline_enhancements, config.getboolean("LOG", 'debug'))
                subprocess.call(cmdline_enhancements, stderr=enhancements_log, stdout=enhancements_log)

                # Generate thumbnails for enhancement map
                thumb_enh_dst = os.path.join(config.get('DIRS', 'img'),
                                             sat_name,
                                             ".thumb_{}-{}-map.jpg".format(file_name_c, enhancements))
                thumb_enh_dst_sm = os.path.join(config.get('DIRS', 'img'),
                                                sat_name,
                                                ".thumb_sm_{}-{}-map.jpg".format(file_name_c, enhancements))

                web.generate_thumbnail(enhancements_out_map, thumb_enh_dst, cfg.THUMBNAILS_NOAA['enh_thumb'])
                web.generate_thumbnail(enhancements_out_map, thumb_enh_dst_sm, cfg.THUMBNAILS_NOAA['enh_thumb_sm'])

                for psikus in open(map_txt, "r").readlines():
                    res = psikus.replace("\n", " \n")
                    enhancements_log.write(res)
                enhancements_log.close()

                if config.getboolean('SCP', 'log'):
                    print cfg.logLineStart + "Sending " + enhancements + " flight and decode logs..." + \
                          cfg.AsciiColors.YELLOW
                    cmdline_scp_log = [config.get("SCP", "bin"),
                                       enhancements_log_file,
                                       config.get('SCP', 'user') + '@' + config.get('SCP', 'host') + ':' +
                                       scp_img_txt_enh]
                    log_cmdline("SCP LOG", cmdline_scp_log, config.getboolean("LOG", 'debug'))
                    subprocess.call(cmdline_scp_log)
                    print cfg.logLineStart + "Sending logs OK, moving on..." + cfg.logLineEnd

                if config.getboolean('SCP', 'img'):
                    print cfg.logLineStart + "Sending " + enhancements + " image with overlay map... " + \
                          cfg.AsciiColors.YELLOW
                    cmdline_scp_img = [config.get("SCP", "bin"),
                                       enhancements_out_map,
                                       config.get('SCP', 'user') + '@' + config.get('SCP', 'host') + ':' +
                                       scp_img_enh]
                    log_cmdline("SCP IMG", cmdline_scp_img, config.getboolean("LOG", 'debug'))
                    subprocess.call(cmdline_scp_img)
                    print cfg.logLineStart + "Send image OK, moving on..." + cfg.logLineEnd

        # SFPG
        if config.getboolean('SCP', 'sfpgLink'):
            path_plik = os.path.join(config.get('DIRS', 'img'), sat_name, "{}-MCIR-precip-map.jpg".format(file_name_c))
            path_plik2 = os.path.join(config.get('DIRS', 'img'), sat_name, "_image.jpg")
            if os.path.isfile(path_plik2):
                os.unlink(path_plik2)
            os.symlink(path_plik, path_plik2)
    else:  # No overlays wanted
        print cfg.logLineStart + 'Creating basic image without map' + cfg.logLineEnd

        img_txt = os.path.join(config.get('DIRS', 'img'), sat_name, "{}-normal.jpg.txt".format(file_name_c))
        out_img = os.path.join(config.get('DIRS', 'img'), sat_name, "{}-normal.jpg".format(file_name_c))
        scp_img_txt = os.path.join(config.get('SCP', 'dir'), "/",
                                   sat_name.replace(" ", "\ "), "{}-normal.jpg.txt".format(file_name_c))
        scp_img = os.path.join(config.get('SCP', 'dir'), "/",
                               sat_name.replace(" ", "\ "), "{}-normal.jpg".format(file_name_c))

        r = open(img_txt, "w+")
        cmdline = [wxtoimg_bin,
                   wxtoimg_cfg['wxQuietOpt'], wxtoimg_cfg['wxDecodeOpt'], wxtoimg_cfg['wxAddText'],
                   '-o', '-R1',
                   '-Q ' + config.get('PROCESSING', 'wxJPEGQuality'),
                   '-t', 'NOAA',
                   in_wav,
                   out_img]
        log_cmdline("WXTOIMG", cmdline, config.getboolean("LOG", 'debug'))
        r.write('\nSAT: ' + str(xf_no_space) + ', Elevation max: ' + str(max_elev) + ', Date: ' + str(filename) + '\n')
        subprocess.call(cmdline, stderr=r, stdout=r)
        r.close()

        for line in open(img_txt,
                         "r").readlines():
            res = line.replace("\n", "")
            res2 = re.sub(r"(\d)", r"\033[96m\1\033[94m", res)
            print cfg.logLineStart + cfg.AsciiColors.OKBLUE + res2 + cfg.logLineEnd

        if config.getboolean('SCP', 'log'):
            print cfg.logLineStart + "Sending flight and decode logs..." + cfg.AsciiColors.YELLOW
            cmdline_scp_log = [config.get("SCP", "bin"),
                               img_txt,
                               config.get('SCP', 'user') + '@' + config.get('SCP', 'host') + ':' + scp_img_txt]
            log_cmdline("SCP LOG", cmdline_scp_log, config.getboolean("LOG", 'debug'))
            subprocess.call(cmdline_scp_log)

        if config.getboolean('SCP', 'img'):
            print cfg.logLineStart + "Sending base image with map: " + cfg.AsciiColors.YELLOW
            cmdline_scp_img = [config.get("SCP", "bin"),
                               out_img,
                               config.get('SCP', 'user') + '@' + config.get('SCP', 'host') + ':' + scp_img]
            log_cmdline("SCP IMG", cmdline_scp_img, config.getboolean("LOG", 'debug'))
            subprocess.call(cmdline_scp_img)
            print cfg.logLineStart + "Sending OK, go on..." + cfg.logLineEnd

        if config.getboolean('PROCESSING', 'wxEnhCreate'):
            for enhancements in config.getlist('PROCESSING', 'wxEnhList'):
                print cfg.logLineStart + 'Creating ' + enhancements + ' image' + cfg.logLineEnd

                enhancements_log_file = os.path.join(config.get('DIRS', 'img'),
                                                     sat_name,
                                                     "{}-nomap.jpg.txt".format(enhancements))
                enhancements_log = open(enhancements_log_file, "w+")
                enhancements_log.write(
                    '\nEnhancement: ' + enhancements + ', SAT: ' + str(xf_no_space) + ', Elevation max: ' + str(
                        max_elev) + ', Date: ' + str(filename) + '\n')

                enhancements_out_map = os.path.join(config.get('DIRS', 'img'),
                                                    sat_name,
                                                    "{}-{}-nomap.jpg".format(file_name_c, enhancements))

                scp_img_txt_enh = os.path.join(config.get('SCP', 'dir'), "/",
                                               sat_name.replace(" ", "\ "),
                                               "{}-{}-nomap.jpg.txt".format(file_name_c, enhancements))
                scp_img_enh = os.path.join(config.get('SCP', 'dir'), "/",
                                           sat_name.replace(" ", "\ "),
                                           "{}-{}-nomap.jpg".format(file_name_c, enhancements))

                cmdline_enhancements = [wxtoimg_bin,
                                        wxtoimg_cfg['wxQuietOpt'], wxtoimg_cfg['wxDecodeOpt'], wxtoimg_cfg['wxAddText'],
                                        '-o', '-K', '-R1',
                                        '-Q ' + config.get('PROCESSING', 'wxJPEGQuality'),
                                        '-e', enhancements,
                                        in_wav,
                                        enhancements_out_map]
                log_cmdline("WXTOIMG ENHANCEMENTS", cmdline_enhancements, config.getboolean("LOG", 'debug'))
                subprocess.call(cmdline_enhancements, stderr=enhancements_log, stdout=enhancements_log)
                enhancements_log.close()

                if config.getboolean('SCP', 'log'):
                    print cfg.logLineStart + "Sending " + enhancements + " flight and decode logs..." + \
                          cfg.AsciiColors.YELLOW
                    cmdline_scp_log = [config.get("SCP", "bin"),
                                       enhancements_log_file,
                                       config.get('SCP', 'user') + '@' + config.get('SCP', 'host') + ':'
                                       + scp_img_txt_enh]
                    log_cmdline("SCP LOG", cmdline_scp_log, config.getboolean("LOG", 'debug'))
                    subprocess.call(cmdline_scp_log)

                if config.getboolean('SCP', 'img'):
                    print cfg.logLineStart + "Sending " + enhancements + " image with overlay map... " + \
                          cfg.AsciiColors.YELLOW
                    cmdline_scp_img = [config.get("SCP", "bin"),
                                       enhancements_out_map,
                                       config.get('SCP', 'user') + '@' + config.get('SCP', 'host') + ':'
                                       + scp_img_enh]
                    log_cmdline("SCP IMG", cmdline_scp_img, config.getboolean("LOG", 'debug'))
                    subprocess.call(cmdline_scp_img)
                    print cfg.logLineStart + "Sending OK, moving on" + cfg.logLineEnd

        if config.getboolean('SCP', 'sfpgLink'):
            path_plik = os.path.join(config.get('DIRS', 'img'), sat_name,
                                     "{}-MCIR-precip-nomap.jpg".format(file_name_c))
            path_plik2 = os.path.join(config.get('DIRS', 'img'), sat_name, "_image.jpg")
            if os.path.isfile(path_plik2):
                os.unlink(path_plik2)
            os.symlink(path_plik, path_plik2)


# Record and transcode wave file
def record_wav(config, frequency, filename, sleep_for, sat_name):
    record_fm(config, frequency, filename, sleep_for, sat_name)
    transcode(config, filename, sat_name)
    if config.getboolean('PROCESSING', 'createSpectro'):
        spectrum(config, filename, sat_name)


def spectrum(config, xfilename, sat_name):
    xf_no_space = sat_name.replace(" ", "")
    print cfg.logLineStart + 'Creating flight spectrum' + cfg.logLineEnd
    cmdline = ['sox',
               os.path.join(config.get('DIRS', 'rec'), "{}-{}.wav".format(xf_no_space, xfilename)),
               '-n', 'spectrogram',
               '-o', os.path.join(config.get('DIRS', 'spec'), "{}-{}.png".format(xf_no_space, xfilename))]
    log_cmdline("SOX SPECTRUM", cmdline, config.getboolean("LOG", 'debug'))
    subprocess.call(cmdline)


def find_next_pass(config):
    tle_file = os.path.join(config.get('DIRS', 'tle'), config.get('DIRS', 'tleFile'))

    predictions = [
        pypredict.aoslos(s,
                         config.get('QTH', 'minElev'),
                         config.get('QTH', 'minElevMeteor'),
                         config.get('QTH', 'lat'),
                         config.get('QTH', 'lon'),
                         config.get('QTH', 'alt'),
                         tle_file) for s in
        config.getlist('BIRDS', 'satellites')]
    aoses = [p[0] for p in predictions]
    next_index = aoses.index(min(aoses))
    return (config.getlist('BIRDS', 'satellites')[next_index],
            config.getlist('BIRDS', 'freqs')[next_index],
            predictions[next_index])


# Now magic
def auto_sat_magic(config, cfg_file):
    # PID management
    pid = str(os.getpid())
    if os.path.isfile(config.get('LOG', 'pid')):
        os.unlink(config.get('LOG', 'pid'))
    file(config.get('LOG', 'pid'), 'w').write(pid)

    # Log config
    if config.getboolean('LOG', 'enable'):
        sys.stdout = Logger(config.get('LOG', 'filename'))

    # wxtoimg command line building
    wxtoimg_cfg = {}
    if config.getboolean('PROCESSING', 'wxQuietOutput'):
        wxtoimg_cfg['wxQuietOpt'] = '-q'
    else:
        wxtoimg_cfg['wxQuietOpt'] = '-C wxQuiet:no'

    if config.getboolean('PROCESSING', 'wxDecodeAll'):
        wxtoimg_cfg['wxDecodeOpt'] = '-A'
    else:
        wxtoimg_cfg['wxDecodeOpt'] = '-C wxDecodeAll:no'

    if config.getboolean('PROCESSING', 'wxAddTextOverlay'):
        wxtoimg_cfg['wxAddText'] = "-k '" + config.get('PROCESSING', 'wxOverlayText') + "' %g %T/%E%p%^%z/e:%e %C"
    else:
        wxtoimg_cfg['wxAddText'] = '-C wxOther:noOverlay'

    # The real magic starts here
    while True:
        (satName, freq, (aosTime, losTime, duration, maxElev, pass_transit, tle_sat)) = find_next_pass(config)
        now = time.time()
        towait = aosTime - now

        aos_time_cnv = strftime('%H:%M:%S', time.localtime(aosTime))
        los_time_cnv = strftime('%H:%M:%S', time.localtime(losTime))

        # OK, now we have to decide what if recording or sleeping
        if towait > 0:
            print cfg.logLineStart + "waiting " + cfg.AsciiColors.CYAN + str(towait).split(".")[
                0] + cfg.AsciiColors.OKGREEN + " seconds  (" + cfg.AsciiColors.CYAN + aos_time_cnv + \
                  cfg.AsciiColors.OKGREEN + " to " + cfg.AsciiColors.CYAN + los_time_cnv + ", " + str(
                duration) + cfg.AsciiColors.OKGREEN + "s.) for " + cfg.AsciiColors.YELLOW + satName + \
                  cfg.AsciiColors.OKGREEN + " @ " + cfg.AsciiColors.CYAN + str(maxElev) + cfg.AsciiColors.OKGREEN + \
                  "\xb0 el. " + cfg.logLineEnd
            write_status(config, freq, aosTime, los_time_cnv, aosTime, towait, satName, maxElev, 'WAITING')
            time.sleep(towait)

        if aosTime < now:
            record_time = losTime - now
            if record_time < 1:
                record_time = 1
        elif aosTime >= now:
            record_time = duration
            if record_time < 1:
                record_time = 1

        pass_ok = True

        fname = str(aosTime)
        print cfg.logLineStart + "Beginning pass of " + cfg.AsciiColors.YELLOW + satName + cfg.AsciiColors.OKGREEN + \
              " at " + cfg.AsciiColors.CYAN + str(maxElev) + "\xb0" + cfg.AsciiColors.OKGREEN + " elev.\n" + \
              cfg.logLineStart + "Predicted start " + cfg.AsciiColors.CYAN + aos_time_cnv + cfg.AsciiColors.OKGREEN + \
              " and end " + cfg.AsciiColors.CYAN + los_time_cnv + cfg.AsciiColors.OKGREEN + ".\n" + cfg.logLineStart + \
              "Will record for " + cfg.AsciiColors.CYAN + \
              str(record_time).split(".")[0] + cfg.AsciiColors.OKGREEN + " seconds." + cfg.logLineEnd
        write_status(config, freq, aosTime, los_time_cnv, str(losTime), str(record_time).split(".")[0],
                     satName, maxElev, 'RECORDING')

        if satName in ('NOAA 15', 'NOAA 19', 'NOAA 18'):
            try:
                record_wav(config, freq, fname, record_time, satName)
            except:
                pass_ok = False
        elif satName == 'METEOR-M 2':
            if config.getboolean("PROCESSING", "recordMeteor"):
                try:
                    record_qpsk(config, cfg_file, record_time)
                except:
                    pass_ok = False
        print cfg.logLineStart + "Decoding data" + cfg.logLineEnd
        if satName in ('NOAA 15', 'NOAA 19', 'NOAA 18') and pass_ok:
            write_status(config, freq, aosTime, los_time_cnv, str(losTime), str(record_time).split(".")[0], satName,
                         maxElev, 'DECODING')
            decode(config, fname, aosTime, satName, maxElev, record_time, wxtoimg_cfg)  # make picture
        elif satName == 'METEOR-M 2' and pass_ok:
            if config.getboolean('PROCESSING', 'decodeMeteor'):
                print "This may take a loooong time and is resource hungry!!!"
                write_status(config, freq, aosTime, los_time_cnv, str(losTime), str(record_time).split(".")[0], satName,
                             maxElev, 'DECODING')
                decode_qpsk(config)

        if pass_ok:
            tle_draw.generate_pass_trace(config, pass_transit, tle_sat, satName, fname)

            # No METEOR currently managed
            # Generate Static uses the CSV records so we should not add METEOR in it if not managed by the static thing
            if 'NOAA' in satName:
                web.add_db_record(config, satName, now, aosTime, losTime, maxElev, record_time)
                web.generate_static_web(config, satName, now, aosTime, losTime, maxElev, record_time)
            else:
                print "METEOR currently not managed for static webpages generation"

        print cfg.logLineStart + "Finished pass of " + cfg.AsciiColors.YELLOW + satName + cfg.AsciiColors.OKGREEN + \
              " at " + cfg.AsciiColors.CYAN + los_time_cnv + cfg.AsciiColors.OKGREEN + ". Sleeping for" + \
              cfg.AsciiColors.CYAN + " 10" + cfg.AsciiColors.OKGREEN + " seconds" + cfg.logLineEnd
        time.sleep(10.0)
