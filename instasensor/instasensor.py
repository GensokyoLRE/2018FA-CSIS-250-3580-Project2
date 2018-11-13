"""
A dummy GCCCD Software Sensor, just to show the very basic functionality of a software sensor.
"""
__version__ = "1.0"
__author__ = "Wolf Paulus"
__email__ = "wolf.paulus@gcccd.edu"

import os
import json
import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from sensor import SensorX
from requests import Timeout, HTTPError, ConnectionError

logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.getcwd(), 'logs', 'instasensor.log'),
    filemode='a',
    format='%(asctime)s - %(lineno)d - %(message)s')


class InstaSensor(SensorX):
    """ requires external lib for screen scraping BeautifulSoup (v4.3.x) and XML and HTML processor lxml (v4.2.x) """

    def __init__(self):
        super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))

    def has_updates(self, k):
        """ find out if there is content beyond k """
        n = 0
        content = self.get_all()  # newest last
        for i in range(len(content)):
            if content[i]['k'] == k:
                n = i + 1
                break
        return len(content) if n == 0 else len(content) - n

    def get_content(self, k):
        """ return new insta posts since k """
        content = self.get_all()  # newest last
        n = 0
        for i in range(len(content)):
            if content[i]['k'] == k:
                n = i + 1
                break
        return content if n == 0 else content[n:]

    def get_all(self):
        """ return list of insta posts .. newest last """
        if self._request_allowed():
            return self._fetch_data()[::-1]
        else:
            return self._read_buffer()[::-1]

    def _fetch_data(self):
        """ json encoded response from webservice .. or none"""
        try:
            response = requests.get(self.props['service_url'] % (self.props['geo_id']),
                                    timeout=self.props['request_timeout'])
            self.props['last_used'] = int(time.time())
            self._save_settings()  # remember time of the last service request
            if response.status_code == 200:
                content = InstaSensor._create_content(response.text)
                self._write_buffer(content)  # remember last service request(s) results.
            else:
                logging.warning("response: {} {} {}".format(response.status_code, response, response.text))
                content = []
        except (HTTPError, Timeout, ConnectionError, KeyError, ValueError, TypeError) as e:
            logging.error("except: " + str(e))
            content = []
        return content

    def get_featured_image(self):
        return self.props['featured_image']

    @staticmethod
    def _create_content(text):
        """ convert the json response from the web-service into a list of dictionaries that meets our needs.
        Parse the json content, which can be found in the javascript of the web page."""
        text = text.replace(u"\u2022", u" ")
        soup = BeautifulSoup(text, 'lxml')
        script = soup.find('script', text=lambda t: t.startswith('window._sharedData'))
        page_json = script.text.split(' = ', 1)[1].rstrip(';')
        data = json.loads(page_json)
        content = []
        for gram in data['entry_data']['LocationsPage'][0]['graphql']['location']['edge_location_to_media']['edges']:
            post = {
                'k': gram['node']['id'],
                'date': str(datetime.fromtimestamp(gram['node']['taken_at_timestamp'])),
                'origin': 'https://www.instagram.com/p/' + gram['node']['shortcode']
            }
            if gram['node']['edge_media_to_caption']['edges']:
                text = gram['node']['edge_media_to_caption']['edges'][0]['node']['text']
                lines = text.split('\n')
                post['caption'] = lines[0].replace("#", " ")
                post['summary'] = text.replace("#", "\#") + "\n\n## Likes: _{}_".format(
                    str(gram['node']['edge_liked_by']['count']))
            if gram['node']['thumbnail_resources'][4]:
                post['img'] = gram['node']['thumbnail_resources'][4]['src']

            content.append(post)
        return content  # newest 1st


if __name__ == "__main__":
    for d in InstaSensor().get_all():
        print(d)
