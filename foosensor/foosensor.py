"""
A dummy GCCCD Software Sensor, just to show the very basic functionality of a software sensor.
"""
__version__ = "2.0"
__author__ = "Wolf Paulus"
__email__ = "wolf.paulus@gcccd.edu"

import os
import time
import logging
import requests
from datetime import datetime, timezone
from requests import Timeout, HTTPError, ConnectionError
from sensor import SensorX

# logging into current_dir/logs/{sensor_name}.log
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.getcwd(), 'logs', 'foosensor.log'),
    filemode='a',
    format='%(asctime)s - %(lineno)d - %(message)s')


class FooSensor(SensorX):
    """ Simply reporting the current time, as reported by api.timezonedb.com
        FooSensor.json is the sensor's config file and FooSensor.buf is the history buffer """

    def __init__(self):
        """ calling the super this a file name, without extension, e.g. './foosensor/FooSensor' """
        super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))
        logging.info("Sensor just woke up .. ready to be called")

    #
    #   Implementing the required methods
    #

    def has_updates(self, k):
        """ find out if there is content beyond k"""
        if self._request_allowed():
            content = self._fetch_data()
            if 0 < len(content) and content[0]['k'] != k:
                return 1
        return 0

    def get_content(self, k):
        """ return content after k"""
        content = self.get_all()
        return content if 0 < len(content) and content[0]['k'] != k else None

    def get_all(self):
        """ return fresh or cached content"""
        if self._request_allowed():
            return self._fetch_data()
        else:
            return self._read_buffer()

    def _fetch_data(self):
        """ json encoded response from webservice .. or none"""
        try:
            response = requests.get(self.props['service_url'] % (self.props['apikey'], self.props['zone']))
            self.props['last_used'] = int(time.time())
            self._save_settings()  # remember time of the last service request
            if response.status_code == 200:
                content = FooSensor._create_content(response.json())
                logging.info("successfully requested new content")
                self._write_buffer(content)  # remember last service request(s) results.
            else:
                logging.warning("response: {} {} {}".format(response.status_code, response, response.text))
                content = None
        except (HTTPError, Timeout, ConnectionError, KeyError, ValueError, TypeError) as e:
            logging.error("except: " + str(e))
            content = None
        return content

    def get_featured_image(self):
        return self.props['featured_image']

    @staticmethod
    def _create_content(ws_json):
        """ convert the json response from the web-service into a list of dictionaries that meets our needs. """
        ts = datetime.fromtimestamp(ws_json['timestamp'], timezone.utc)
        m, h = ts.time().minute, ts.time().hour
        if m >= 45:
            h += 1
        h = 12 if h == 0 else h % 12
        if 15 < m < 45:
            h = h * 100 + 30
        icon = "clock{}.png".format(h)

        d = {'k': ws_json['timestamp'],
             'date': ts.strftime('%Y-%m-%d %I:%M:%S %p'),
             'caption': 'Current time at Grossmont College',
             'summary': 'It\'s currently {} at the **Grossmont–Cuyamaca Community College District**'.format(
                 ts.strftime("%I:%M:%S %p")),
             'story': 'Like everywhere in the _{}_ time-zone, the local time at the **Grossmont–Cuyamaca Community '
                      'College District** is currently {}'.format(ws_json['zoneName'], ts.strftime("%I:%M:%S %p")),
             'img': 'https://www.webpagefx.com/tools/emoji-cheat-sheet/graphics/emojis/' + icon
             }
        return [d]


if __name__ == "__main__":
    """ let's play """
    sensor = FooSensor()

    for i in range(10):
        print(sensor.get_all())
        time.sleep(1)  # let's relax for short while

    n = 0
    for i in range(10):
        if sensor.has_updates(n):
            ld = sensor.get_content(n)  # list of dictionaries
            print(ld)
            n = ld[0]['k']
        time.sleep(1)  # let's relax for short while
        print("sleeping ...")
