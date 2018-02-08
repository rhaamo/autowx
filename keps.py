import os
import requests

keps_to_manage = {
    'noaa.txt': 'https://www.celestrak.com/NORAD/elements/noaa.txt',
    'amateur.txt': 'https://www.celestrak.com/NORAD/elements/amateur.txt',
    'cubesat.txt': 'https://www.celestrak.com/NORAD/elements/cubesat.txt',
    'weather.txt': 'https://www.celestrak.com/NORAD/elements/weather.txt',
    'multi.txt': 'http://www.pe0sat.vgnet.nl/kepler/mykepler.txt',
}


def update_keps(config, force):
    for keps_name,keps_url in keps_to_manage.iteritems():
        print "Downloading keps {} from {}".format(keps_name, keps_url)
        file_destination = os.path.join(config.get('DIRS', 'tle'), keps_name)
        if os.path.isfile(file_destination):
            if force:
                os.unlink(file_destination)
            else:
                print 'Force not asked, ignoring update.'
                continue

        r = requests.get(keps_url)
        with open(file_destination, "wb") as keps_file:
            keps_file.write(r.content)
            print "File saved as {}".format(file_destination)
