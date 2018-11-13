""" A Software Sensor using the OpenWeatherMap API """
import os
import time
import logging
from datetime import datetime
import requests
from requests import Timeout, HTTPError, ConnectionError
from sensor import SensorX

# logging into current_dir/logs/{sensor_name}.log
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.getcwd(), 'logs', 'openweathersensor.log'),
    filemode='a',
    format='%(asctime)s - %(lineno)d - %(message)s')


class OpenWeather(SensorX):
    """ Simply reporting the current time, as reported by api.timezonedb.com
        FooSensor.json is the sensor's config file and FooSensor.buf is the history buffer """

    def __init__(self):
        """ calling the super this a file name, without extension """
        super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))

    def get_all(self):
        """ return fresh or cached content"""
        if self._request_allowed():
            return self._fetch_data()
        else:
            return self._read_buffer()

    def _fetch_data(self):
        """ json encoded response from webservice .. or none"""
        try:
            response = requests.get(self.props['service_url'] % (
                50, self.props['city'], self.props['countrycode'], self.props['units'], self.props['apikey']))
            self.props['last_used'] = int(time.time())
            self._save_settings()  # remember time of the last service request
            if response.status_code == 200:
                content = self._create_content(response.json())
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
        if ws_json['cod'] == '200':
            m = max(ws_json['list'], key=lambda item: int(item['main']['temp_max']))
            ts0 = datetime.now()
            tsx = datetime.fromtimestamp(m['dt'])
            d = {'k': ts0,
                 'date': ts0.strftime('%Y-%m-%d %I:%M:%S %p'),
                 'caption': 'Temperature forecast for Grossmont College',
                 'summary': 'For Grossmont College, the warmest temperature of **{} F** is forecast for {}'.format(
                     m['main']['temp_max'], tsx.strftime("%A %I:%M:%S %p"))
                 }
            return [d]
        return []


if __name__ == "__main__":
    """ let's play """
    sensor = OpenWeather()
    print(sensor.get_all())
