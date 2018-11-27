"""
Author: Riyam Arabo
Last updated: 11/15/2018
Version: 1.0
Purpose: To collect data from Meetup.com's API regarding upcoming events related to programming
"""
import logging
from sensor import SensorX
import os
import time
from requests import Timeout, HTTPError, ConnectionError
import requests
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.getcwd(), 'logs', 'meetup.logs'),
    filemode='a',
    format='%(asctime)s - %(lineno)d - %(message)s')


class Meetup(SensorX):

    def __init__(self):
        """ read sensor settings from config file """
        super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))

    def has_updates(self, k):
        """ finding out if there are new updates since last API request 'k' """
        n = 0
        content = self.get_all()
        for i in range(len(content)):
            if content[i]['k'] == k:
                n = i + 1
                break
        return len(content) if n == 0 else len(content) - n

    def get_content(self, k):
        """ return new events since last request 'k' """
        content = self.get_all()  # newest last
        n = 0
        for i in range(len(content)):
            if content[i]['k'] == k:
                n = i + 1
                break
        return content if n == 0 else content[n:]

    def get_all(self):
        if self._request_allowed():
            return self._fetch_data()[::-1]
        else:
            return self._read_buffer()[::-1]

    def _fetch_data(self):
        """ json encoded response from webservice .. or none"""
        try:
            response = requests.get(
                self.props['service_url'] % (self.props['topic_category'], self.props['radius'], self.props['key']),
                timeout=self.props['request_timeout'])
            self.props['last_used'] = int(time.time())
            self._save_settings()  # remember time of the last service request
            if response.status_code == 200:
                content = Meetup._create_content(response.json())
                self._write_buffer(content)  # remember last service request(s) results.
            else:
                logging.warning("response: {} {} {}".format(response.status_code, response, response.json()))
                content = []
        except (HTTPError, Timeout, ConnectionError, KeyError, ValueError, TypeError) as e:
            logging.error("except: " + str(e))
            content = []
        return content

    @staticmethod
    def _create_content(text):
        """ convert the json response from the web-service into a list of dictionaries that meets our needs."""
        record = []
        n = 0
        for event in text['events']:
            description = event.get('description', "no description found")
            if 'venue' in event:
                data = {'k': event['name'],
                        'date': str(datetime(int(event['local_date'][0:4]),
                                             int(event['local_date'][5:7]),
                                             int(event['local_date'][8:10]),
                                             int(event['local_time'][0:2]),
                                             int(event['local_time'][3:5]))),
                        'caption': event['name'],
                        'summary': 'An event held by {} for {}'.format(
                            event['group'].get('name'),
                            event['group'].get('who')),
                        'story': description,
                        'origin': event['link']}
                n += 1
                record.append(data)

        logging.info("number of records: " + str(n))
        return record  # newest 1st


if __name__ == "__main__":

    sensor = Meetup()

    n = 0
    for i in range(5):
        if sensor.has_updates(n):
            json_doc = sensor.get_all()
            print(json_doc)
            time.sleep(4)
            print("now we sleep")
