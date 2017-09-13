# -*- coding: utf-8 -*-
import predict
import time
from time import strftime
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import os
import datetime

matplotlib.use('Agg')


def generate_pass_trace(config, transit, sat_name, sat_timestamp):
    # Config
    qth = (config.getfloat('QTH', 'lat'), config.getfloat('QTH', 'lon'), config.getint('QTH', 'alt'))

    file_name_c = datetime.datetime.fromtimestamp(sat_timestamp).strftime('%Y%m%d-%H%M')
    out_img = os.path.join(config.get('DIRS', 'img'), sat_name, "{}-sky-trace.jpg".format(file_name_c))

    # The rest

    font = {'color': '#212121', 'size': 8, }
    font2 = {'color': '#00796B', 'size': 12, }

    f = predict.quick_predict(sat_name, transit.start, qth)
    predict_xp = []
    predict_yp = []
    predict_time = []
    predict_table = []

    for md in f:
        predict_yp.append(90 - md['elevation'])
        predict_xp.append(md['azimuth'])
        predict_time.append(int(md['epoch']))

    for ed, ag in enumerate(predict_xp):
        predict_table.append(
            {'time': strftime('%H:%M:%S', time.localtime(predict_time[ed])),
             'azi': np.radians(predict_xp[ed]),
             'elev': 90 - predict_yp[ed],
             'elunc': predict_yp[ed]})

    theta = np.radians(predict_xp)
    zeniths = predict_yp
    plt.ioff()

    ax = matplotlib.pyplot.figure(figsize=(4.0, 4.0))
    ax = plt.subplot(111, projection='polar', axisbg='#ECEFF1')  # create figure & 1 axis
    ax.set_xticklabels([])
    ax.set_yticklabels([])

    grid_x, grid_y = 45.0, 45.0
    parallel_grid = np.arange(-90.0, 90.0, grid_x)
    meridian_grid = np.arange(-180.0, 180.0, grid_y)
    ax.text(0.5, 1.025, 'N', transform=ax.transAxes, horizontalalignment='center',
            verticalalignment='bottom',
            size=12)
    for para in np.arange(grid_y, 360, grid_y):
        x = (1.1 * 0.5 * np.sin(np.deg2rad(para))) + 0.5
        y = (1.1 * 0.5 * np.cos(np.deg2rad(para))) + 0.5
        ax.text(x, y, u'%i\N{DEGREE SIGN}' % para, transform=ax.transAxes, horizontalalignment='center',
                verticalalignment='center', fontdict=font2)
    ax.set_aspect('auto', adjustable='datalim')
    ax.set_autoscale_on(True)
    ax.set_rmax(90)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.plot(np.linspace(0, 2 * np.pi, 100), np.ones(100) * 90, color='#0d47a1', linestyle='-')
    ax.plot(theta, zeniths, '-', color='#00695C', lw=2)
    ax.plot(theta, zeniths, '.', color='#0d47a1', alpha=0.4, lw=2)

    for mc in predict_table:
        ax.text(mc['azi'], mc['elunc'], ' ' + mc['time'] + ' ' + str(int(mc['elev'])) + '$^\circ$',
                fontdict=font)

    plt.savefig(out_img)  # save the figure to file
    plt.close()  # close the figure
