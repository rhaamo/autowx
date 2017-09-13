#!/usr/bin/env python
# -*- coding: utf-8 -*-

import predict


def aoslos(satname, min_elev, min_elev_meteor, station_lat, station_lon, station_alt, tle_file):
    tle_noaa15 = []
    tle_noaa18 = []
    tle_noaa19 = []
    tle_meteor = []

    tlefile = open(str(tle_file))
    tledata = tlefile.readlines()
    tlefile.close()

    for i, line in enumerate(tledata):
        if "NOAA 15" in line:
            for l in tledata[i:i + 3]:
                tle_noaa15.append(l.strip('\r\n').rstrip()),
    for i, line in enumerate(tledata):
        if "NOAA 18" in line:
            for m in tledata[i:i + 3]:
                tle_noaa18.append(m.strip('\r\n').rstrip()),
    for i, line in enumerate(tledata):
        if "NOAA 19" in line:
            for n in tledata[i:i + 3]:
                tle_noaa19.append(n.strip('\r\n').rstrip()),
    for i, line in enumerate(tledata):
        if "METEOR-M 2" in line:
            for n in tledata[i:i + 3]:
                tle_meteor.append(n.strip('\r\n').rstrip()),

    qth = (float(station_lat), float(station_lon), float(station_alt))
    min_elev = int(min_elev)
    min_elev_meteor = int(min_elev_meteor)
    # Recording delay
    delay = '1'
    # delay meteor to ~12° - 15°
    meteor_delay = '180'
    # Recording short
    short = '1'
    # Shorten meteor recording by ~12° - 15°
    meteor_short = '180'
    # Predicting
    if satname in "NOAA 15":
        p = predict.transits(tle_noaa15, qth)
        for i in range(1, 20):
            transit = p.next()
            aos_start = int(transit.start) + int(delay)
            aos_time = int(transit.duration()) - (int(short) + int(delay))
            aos_end = int(aos_start) + int(aos_time)
            if int(transit.peak()['elevation']) >= min_elev:
                return int(aos_start), int(aos_end), int(aos_time), int(transit.peak()['elevation']), transit
    elif satname in "NOAA 18":
        p = predict.transits(tle_noaa18, qth)
        for i in range(1, 20):
            transit = p.next()
            aos_start = int(transit.start) + int(delay)
            aos_time = int(transit.duration()) - (int(short) + int(delay))
            aos_end = int(aos_start) + int(aos_time)
            if int(transit.peak()['elevation']) >= min_elev:
                return int(aos_start), int(aos_end), int(aos_time), int(transit.peak()['elevation']), transit
    elif satname in "NOAA 19":
        p = predict.transits(tle_noaa19, qth)
        for i in range(1, 20):
            transit = p.next()
            aos_start = int(transit.start) + int(delay)
            aos_time = int(transit.duration()) - (int(short) + int(delay))
            aos_end = int(aos_start) + int(aos_time)
            if int(transit.peak()['elevation']) >= min_elev:
                return int(aos_start), int(aos_end), int(aos_time), int(transit.peak()['elevation']), transit
    elif satname in "METEOR-M 2":
        p = predict.transits(tle_meteor, qth)
        for i in range(1, 20):
            transit = p.next()
            aos_start = int(transit.start) + int(meteor_delay)
            aos_time = int(transit.duration()) - (int(meteor_short) + int(meteor_delay))
            aos_end = int(aos_start) + int(aos_time)
            if int(transit.peak()['elevation']) >= min_elev_meteor:
                return int(aos_start), int(aos_end), int(aos_time), int(transit.peak()['elevation']), transit
    else:
        print "NO TLE DEFINED FOR " + satname + " BAILING OUT"
