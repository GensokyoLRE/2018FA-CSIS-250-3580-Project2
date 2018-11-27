""" 
Robert Schult
CSIS 250
Project 2
Software Sensor Application
"""

import os
import time
import json
from datetime import datetime
import requests
from requests import Timeout, HTTPError, ConnectionError
from sensor import SensorX


class SatSensor(SensorX):

    def __init__(self):
        super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))
        self.sat_responses = {}
        print("This sensor just woke up .. ready to call " + self.props.get('service_url'))

    def __str__(self):
        return (self.get_all())

    def _fetch_data(self):
        # Runs the rest api request to get the current list of satleites overhead.
        try:
            content = []
            response = requests.get(
                self.props.get('service_url')
                + self.props.get('location_lat')
                + '/' + self.props.get('location_lon')
                + '/' + self.props.get('location_alt')
                + '/' + self.props.get('search_arc')
                + '/' + self.props.get('sat_category')
                + '/&apiKey=' + self.props.get('api_key')
            )
            self.props['last_used'] = int(time.time())
            self._save_settings()
            if response.status_code == 200:
                print("Good Response")
                content = self._create_content(response.text)
                print("Content Created")
                if content is not None:
                    self._write_buffer(content)
            else:
                print("Bad Response")
                return None
        except (HTTPError, Timeout, ConnectionError, KeyError, ValueError, TypeError) as e:
            # logging.error("except: " + str(e))
            print("Error Occured:" + str(e))
            content = None
        return content

    def _create_content(self, json_string):
        timestamp = datetime.now()
        unixstamp = int(time.time())
        sats = []
        sat_json = json.loads(json_string)
        print("Creating Content...")
        if (sat_json['info']['satcount'] > 0):
            for sat in sat_json["above"]:
                sats.append(sat["satname"])
            d = {'k': unixstamp,
                 'caption': 'Satelites over Grossmont',
                 'summary': 'Here are some of the sattelites currently passing over grossmont right now!',
                 'story': 'As of {} the following satelites are overhead: {}'.format(
                     timestamp.strftime("%B %d, %Y at %I:%M:%S %p"), ', '.join(map(str, sats))),
                 'img': self.get_featured_image()
                 }
            return [d]
        else:
            print("no sats")
            return None

    def get_featured_image(self):
        sat_images = {
            "0": "https://s3.amazonaws.com/content.satimagingcorp.com/media/cms_page_media/1601/TH-01.jpg",
            "1": "https://spacenews.com/wp-content/uploads/2017/08/rsz_echostarJup3-879x485.jpg",
            "2": "https://upload.wikimedia.org/wikipedia/commons/0/04/International_Space_Station_after_undocking_of_STS-132.jpg",
            "15": "http://www.davidiad.com/images/iridium/iridium_b.jpg",
            "18": "https://s3.amazonaws.com/content.satimagingcorp.com/media/cms_page_media/1601/TH-01.jpg"
        }
        return sat_images[self.props.get('sat_category')]

    def get_all(self):
        """ return fresh or cached content"""
        if self._request_allowed():
            print("Requesting...")
            data = self._fetch_data()
            if data is not None:
                return data
            else:
                return self._read_buffer()
        else:
            return self._read_buffer()

    def has_updates(self, k):
        """ find out if there is content beyond k """
        n = 0
        content = self.get_all()
        for i in range(len(content)):
            if content[i]['k'] == k:
                n = i + 1
                break
        return len(content) if n == 0 else len(content) - n

    def get_content(self, k):
        content = self.get_all()
        n = 0
        for i in range(len(content)):
            if content[i]['k'] == k:
                n = i + 1
                break
        return content if n == 0 else content[n:]


if __name__ == "__main__":
    sr = SatSensor()
    print("Sat Data : " + str(sr.get_all()))
    time.sleep(20)
    updates = sr.has_updates(0)
    print("# Updates : " + str(updates))
    if updates > 0:
        print("Updates : " + str(sr.get_content(updates)))
