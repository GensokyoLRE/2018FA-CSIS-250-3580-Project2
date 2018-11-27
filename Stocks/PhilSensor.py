"""
Program: PhilSensor.py
Author: Phillip "Hifumi" Cuesta (source by Wolfgang Paulus)
Last Mod: 11/8/18 8:20 PM
Purpose: Scans stocks pertinent to the local San Diego area.
Addendum:
Data provided for free by IEX (https://iextrading.com/developer).
View IEX’s Terms of Use (https://iextrading.com/api-exhibit-a/).
"""
import os
from sensor import SensorX
import json
import time
import requests
from datetime import datetime
import logging

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'PhilSensor.json')
startTime = time.time()

logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.getcwd(), 'logs', 'phillipsensor.logs'),
    filemode='a',
    format='%(asctime)s - %(lineno)s - %(message)s'
)


class PhilSensor(SensorX):
    """
    Sensor used in conjunction with the SensorX method of sensor.py in order
    to get data from the IEX server based on each stock from the .json config.
    """

    def __init__(self):
        """ read sensor settings from config file """
        super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))
        self.__url = self.props.get('service_url')
        self.ticks = self.props.get('ticks')
        for index in range(len(self.ticks)):
            self.get_content(index)

    def has_updates(self, k):
        """
        Checks if a file actually needs an update or if it's completely fine as is.
        Arguements:
            int k (index of stock)
        """
        response = requests.get(self.__url % self.ticks[k])
        self.__j_response = response.json()
        up_point = os.path.join(os.path.dirname(__file__), "tickFile",  self.ticks[k] + ".json")
        with open(up_point, 'r') as updateRead:
            read_it = json.load(updateRead)
        j_response = read_it
        if self.__j_response == j_response:
            logging.info("%s.json has the same data." % k)
        else:
            with open(up_point, 'w') as updateWrite:
                json.dump(self.__j_response, updateWrite)
            self.props['last_stamp'] = datetime.strftime(datetime.now(), '%B %d, %Y [%H:%M:%S %p]')
            self._save_settings()
            logging.info("%s.json is now updated." % k)

    def get_content(self, k):
        """
        Gets the content from the IEX server based on the stock provided in variable k.
        :param k: stock ticker index
        :return: Returns if it can update and move on or not.
        """
        response = requests.get(self.__url % self.ticks[k])
        self.__j_response = response.json()
        pointer = os.path.join(os.path.dirname(__file__), "tickFile",  self.ticks[k] + ".json")
        if not os.path.isfile(pointer):
            self.props['last_stamp'] = datetime.strftime(datetime.now(), '%B %d, %Y [%H:%M:%S %p]')
            self._save_settings()
            with open(pointer, 'w') as updater:
                json.dump(self.__j_response, updater)
            with open(CONFIG_FILE, 'w') as settingUpdate:
                json.dump(self.props, settingUpdate)
            self.props['last_request'] = int(time.time())
            logging.info("Data created for %s." % pointer)
        else:
            self.props['last_stamp'] = datetime.strftime(datetime.now(), '%B %d, %Y [%H:%M:%S %p]')
            logging.info("Data exists. Checking update on %s." % pointer)
            self._save_settings()
            self.has_updates(k)

    def get_all(self):
        """
        Gets all data locally stored on the stocks given
        :return: Returns all files as loaded JSONs.
        """
        all_list, patterns = [], ['k', 'date', 'caption', 'summary', 'story', 'img', 'origin']
        x = 0
        for gtick in self.ticks:
            pointer = os.path.join(os.path.dirname(__file__), "tickFile", gtick + ".json")
            pattern_final = {}
            with open(pointer, 'r') as allRead:
                read_out = json.load(allRead)
            with open(CONFIG_FILE, 'r') as setRead:
                set_read_out = json.load(setRead)

            app_pattern = [x,
                           set_read_out['last_stamp'],
                           "%s's Stock History from a Month + News  "
                           % read_out[str(gtick).upper()]['quote']['companyName'],
                           "Last Month Stock reports and last news report for %s  "
                           % read_out[str(gtick).upper()]['quote']['companyName'],
                           read_out[str(gtick).upper()]['news'][0]['summary'],
                           "https://ak2.picdn.net/shutterstock/videos/19066642/thumb/1.jpg",
                           read_out[str(gtick).upper()]['news'][0]['url']]
            pattern_arr = 0
            while pattern_arr < len(patterns):
                pattern_final[patterns[pattern_arr]] = app_pattern[pattern_arr]
                pattern_arr += 1
            x += 1
            all_list.append(pattern_final)
        return all_list

    def can_request(self):
        """
        :return: Returns if the updater is under the delta to update or needs to wait longer.
        """
        return int(time.time() - self.props['last_request'] > self.props['request_delta'])

    def __eq__(self, other):
        """
        Overrider for default __eq__ method
        :param other: item to compare to
        :return: True or False
        """
        if isinstance(other, PhilSensor):
            return self.__j_response == other.__j_response
        return False


if __name__ == "__main__":
    for d in PhilSensor().get_all():
        for key in d.keys():
            print("{} : {}".format(key, d.get(key)))
