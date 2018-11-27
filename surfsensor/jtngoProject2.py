""" CSIS 250 - Project 2 - created by jtngo
A software sensor utilizing MagicSeaweed's API to provide a surf report for San Diego's Mission Beach.
"""
import os
import time
import logging
import json
from datetime import datetime
import requests
from requests import Timeout, HTTPError, ConnectionError
from sensor import Sensor

__title__ = "Mission Beach Surf Report"
__version__ = "2.0"
__author__ = "Jonathan T Ngo"
__url__ = "http://magicseaweed.com/api/66c79af0fe4e3fb73b3915ea2ef63999/forecast/?spot_id=297"

##logging
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join('jtngoProject2.log'),
    filemode='a',
    format='%(asctime)s - %(lineno)d - %(message)s')

class communityInfo(Sensor):
    CONFIG_FILE = 'communityInfo_CONFIG.json'

    def __init__(self):
        """ read sensor settings from config file """
        with open(os.path.join(os.path.dirname(__file__), communityInfo.CONFIG_FILE)) as json_text:
            self.__settings = json.load(json_text)
        print(self.__settings)

    ##protection from issuing too many requests during trial phase
    def __fetch_data(self):
        """json encoded response from webservice or a list of dictionaries"""
        try:
            if not self.__offline:
                text = requests.get(self.__url).text
                self.__settings['last_request'] = str(int(time.time()))
                with open('response.txt', 'w') as backup:
                    backup.write(text)
            else:
                with open('response.txt') as backup:
                    text = backup.read()
        except (ConnectionError, ValueError, TimeoutError) as e:
            logging.error("except: " + str(e))
            content = None
        return content


    def get_content(self, k):
        ##process data
        self.__url = self.__settings.get('http://magicseaweed.com/api/66c79af0fe4e3fb73b3915ea2ef63999'
                                         '/forecast/?spot_id=4209')
        apikey = '66c79af0fe4e3fb73b3915ea2ef63999'
        url = 'http://magicseaweed.com/api/66c79af0fe4e3fb73b3915ea2ef63999/forecast/?spot_id=297'

        response = requests.get(url)
        internal_data = response.json()
        surf_data = json.dumps(internal_data)
        loaded_surf_data = json.loads(surf_data)
        type(surf_data)
        type(loaded_surf_data)

        with open('surf_data.json', 'w') as outfile:
            json.dump(surf_data, outfile)

        ##organize information
        parsed = json.loads(surf_data)
        json.dumps(parsed, indent=4, sort_keys=True)

        for item in parsed:
            return [{'timestamp': datetime.now().strftime('%Y-%m-%d %I:%M:%S %p'),
                 'Mission Beach Surf Report': [parsed]}]

        #myList = []
        #for record in internal_data[0]:
            #myList.append(record['main'].get('timestamp'))
            #if record in myList:
                #myList.append(record['main'].get('timestamp'))
            #print(myList)
            #print()
        pass

    @staticmethod
    def _create_content(ws_json):
        """ convert the json response from the web-service into a list of dictionaries that meets our needs. """
        if ws_json['cod'] == '200':
            m = max(ws_json['list'], key=lambda item: int(item['main']['temp_max']))
            ts0 = datetime.now()
            tsx = datetime.fromtimestamp(m['dt'])
            d = {'k': ts0,
                 'date': ts0.strftime('%Y-%m-%d %I:%M:%S %p'),
                 'caption': 'Mission Beach Surf Report',
                 'summary': 'the warmest temperature of **{} F** is forecast for {}'.format(
                     m['main']['temp_max'], tsx.strftime("%A %I:%M:%S %p"))
                 }
            return [d]
        return []

    def has_updates(self, k):
        """find out if there is content past k"""
        if self._request_allowed():
            content = self._fetch_data()
            if 0 < len(content) and content[0]['k'] != k:
                return 1
        return 0

    def get_all(self):
        """ A list containing all available records oldest first. """
        if self._request_allowed():
            return self._fetch_data()
        else:
            return self._read_buffer()

    #def get_featured_image(self):
        #return self.props['featured_image']

if __name__ == "__main__":
    sensor = communityInfo()

    for i in range(1000):
        json_doc = sensor.get_content(0)
        #print(json_doc)
        print(sensor.get_featured_image())
        time.sleep(300)  ##refreshes every five minutes
