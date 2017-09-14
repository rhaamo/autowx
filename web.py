# -*- coding: utf-8 -*-
from jinja2 import FileSystemLoader, Environment
import math
from wand.image import Image
import os
import datetime
import cfg
import time
import models


def add_db_record(config, sat_name, automate_started, aos_time, los_time, max_elev, record_time):
    engine = models.init(config)
    session_maker = models.get_session(engine)
    session = session_maker()

    sat_pass = models.Passes()
    sat_pass.sat_name = sat_name
    sat_pass.automate_started = automate_started
    sat_pass.aos_time = aos_time
    sat_pass.los_time = los_time
    sat_pass.max_elev = max_elev
    sat_pass.record_time = record_time

    session.add(sat_pass)
    session.commit()


def format_datetime(date, utc=False, fmt=None):
    if type(date) == str:
        date = float(date)

    if not fmt:
        fmt = '%Y-%m-%d %H:%M:%S'

    if utc:
        return datetime.datetime.utcfromtimestamp(date).strftime(fmt)

    return datetime.datetime.fromtimestamp(date).strftime(fmt)


def generate_thumbnail(src, dst, size):
    if not os.path.isfile(src):
        print cfg.logLineStart + "Issue generating thumbnail, file not found: {}".format(src) + cfg.logLineEnd
        return

    with Image(filename=src) as f:
        f.resize(size[0], size[1])
        f.save(filename=dst)

    print cfg.logLineStart + "Generated thumbnail {}x{}: {}".format(size[0], size[1], dst) + cfg.logLineEnd


def sat_type(sat_name):
    if 'NOAA' in sat_name:
        return 'NOAA'
    elif 'METEOR' in sat_name:
        return 'METEOR'
    else:
        return 'OTHER'


def static_web_generation(config):
    engine = models.init(config)
    session = models.get_session(engine)

    # Latest first
    passes = session.query(models.Passes).order_by(models.Passes.aos_time.asc())

    print passes


# Meteor is currently not managed
def generate_static_web(config, sat_name, automate_started, aos_time, los_time, max_elev, record_time):
    if not config.getboolean("PROCESSING", "staticWeb"):
        return

    engine = models.init(config)
    session = models.get_session(engine)

    cur_path = os.path.dirname(os.path.abspath(__file__))
    template_env = Environment(
        autoescape=False,
        loader=FileSystemLoader(os.path.join(cur_path, 'templates')),
        trim_blocks=False)
    template_env.filters['datetime'] = format_datetime

    def render_template(template, context):
        return template_env.get_template(template).render(context)

    emerge_time_utc = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(aos_time))

    if not os.path.exists(config.get("DIRS", "staticWeb")):
        print cfg.logLineStart + "PATH for static web doesn't exist, can't generate web pages" + cfg.logLineEnd
        return

    # Generate the web page of the pass itself

    # time is UTC
    dst_single_pass = os.path.join(
        config.get("DIRS", "staticWeb"), "{}.html".format(emerge_time_utc.replace(":", "-")))

    # timestamp - local time
    img_tstamp = datetime.datetime.fromtimestamp(aos_time).strftime('%Y%m%d-%H%M')
    with open(dst_single_pass, 'w') as f:
        ctx = {
            'sat_name': sat_name,
            'aos_time': aos_time,  # localtime
            'los_time': los_time,  # localtime
            'automate_started': automate_started,  # UTC (from time.time())
            'max_el': max_elev,
            'record_time': record_time,
            'img_tstamp': img_tstamp,
            'sat_type': sat_type(sat_name),
        }

        if config.getboolean('PROCESSING', 'wxEnhCreate'):
            ctx['enhancements'] = []
            for enhancement in config.getlist('PROCESSING', 'wxEnhList'):
                filename = "{}-{}-map.jpg".format(img_tstamp, enhancement)
                ctx['enhancements'].append({
                    'name': enhancement,
                    'img_path': filename,
                    'img_full_path': os.path.join("/img_noaa", sat_name, filename),
                    'log': "{}.txt".format(os.path.join("/img_noaa", sat_name, filename)),
                })

        if config.getboolean('PROCESSING', 'createSpectro'):
            filename = "{}-{}.png".format(sat_name.replace(" ", ""), str(aos_time))
            ctx['spectro'] = {
                'filename': os.path.join("/spectro_noaa", filename)
            }

        html = render_template(config.get('STATIC_WEB', 'single_pass'), ctx)
        f.write(html)
        print cfg.logLineStart + "Wrote web page for single NOAA pass" + cfg.logLineEnd

    # Generate the home page of the passes
    # The CSV is filled even if no static web generation is activated
    # Cycle over the CSV, regenerating home plus every pages splitted on config.passes_per_page

    # Latest first
    passes = session.query(models.Passes).order_by(models.Passes.aos_time.asc())

    # (re)generate the home page
    passes_per_pages = config.getint('STATIC_WEB', 'passes_per_page')

    page = 0
    pages = int(math.ceil(float(len(passes)) / float(passes_per_pages)))
    home_passes = passes[0:passes_per_pages]

    index_page = os.path.join(
        config.get("DIRS", "staticWeb"), "index.html")
    with open(index_page, 'w') as f:
        ctx = {
            'passes': home_passes,
            'passes_per_pages': passes_per_pages,
            'start': 0,
            'total': len(passes),
            'page': page,
            'pages': pages,
            'pages_list': range(0, pages),
        }
        html = render_template(config.get('STATIC_WEB', 'index_passes'), ctx)
        f.write(html)
        page = 1  # index created, increment page
        print cfg.logLineStart + \
              "Wrote web page for index passes, page 0 0-{}".format(passes_per_pages) + \
              cfg.logLineEnd

    if len(passes) > passes_per_pages:
        # We have more pages to show
        for p in range(1, pages):
            start_passes = (page * passes_per_pages)
            page_passes = passes[start_passes:start_passes + passes_per_pages]
            passes_page = os.path.join(config.get("DIRS", "staticWeb"), "index_{}.html".format(page))

            with open(passes_page, 'w') as f:
                ctx = {
                    'passes': page_passes,
                    'passes_per_pages': passes_per_pages,
                    'start': start_passes,
                    'total': len(passes),
                    'page': page,
                    'pages': pages,
                    'pages_list': range(0, pages),
                }
                html = render_template(config.get('STATIC_WEB', 'index_passes'), ctx)
                f.write(html)
                print cfg.logLineStart + "Wrote web page for index passes, page {} {}-{}".format(
                    page, start_passes, start_passes + passes_per_pages
                ) + cfg.logLineEnd
            page = page + 1  # page created, increment

    print cfg.logLineStart + "Finished web page processing" + cfg.logLineEnd
