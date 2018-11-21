""" A Software Sensor using the OpenWeatherMap API (https://openweathermap.org/api/uvi) """
import os
import time
import logging
import requests
from requests import Timeout, HTTPError, ConnectionError
from sensor import SensorX

# Checks to see if the directory for logging exists. If not, it creates it.
if not os.path.exists(os.path.join(os.getcwd(), 'logs')):
    os.makedirs(os.path.join(os.getcwd(), 'logs'))

# logging into current_dir/logs/{sensor_name}.log
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.getcwd(), 'logs', 'uvindex.log'),
    filemode='a',
    format='%(asctime)s - %(lineno)d - %(message)s')


class UVIndex(SensorX):
    """ Reports """

    def __init__(self):
        super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))
        logging.info("Sensor " + self.__class__.__name__ + " initialized.")

    #
    #   Implementing the required methods
    #

    def has_updates(self, k):
        """ find out if there is content beyond k """

        # check to see if we are allowed to fetch from the API (they only allow 1 fetch per 10 minutes)
        if self._request_allowed():
            # get the cache content
            old_content = self._read_buffer()

            # check to make sure the cache content exist (it won't exist if it's the 1st time running the sensor)
            if old_content is not None and len(old_content) > 0:
                # for each dictionary (UV Index content), if our 'k' (current time in epoch) is greater
                # than ANY date (epoch seconds) than there are new forecast to fetch; this means our cache data is stale
                for forecast_day in old_content:
                    if k > forecast_day['date']:
                        logging.info('New updates available.')
                        logging.debug(
                            'Current epoch time: ' + str(k) + ' cache content epoch time: ' + str(forecast_day['date']))
                        return 1
            else:  # there was never any cache data, so fetch it.
                fetched_content = self._fetch_data()
                # check to make sure there is content from the fetch. The fetch data could contain the same 8 days, but
                # the value of the UV Index might have change due to environmental factors; so check if they old != new
                if fetched_content is not None and len(fetched_content) > 0 and old_content != fetched_content:
                    logging.info('New updates available.')
                    return 1
        return 0

    def get_content(self, k):
        """ return content after k """
        # get the content from the API or cache depending on Service calls never overstep their limits constraint
        c = self.get_all()

        # check to see if that the fetch/cache data exist and has content
        if c is not None and len(c) > 0:
            content_after_k = []  # new contents from 'k' date (epoch seconds)
            for forecast_day in c:
                # if the fetch/cache data's date (epoch seconds) are in the future,
                # then those are contents after 'k' (epoch seconds)
                if forecast_day['date'] > k:
                    content_after_k.append(forecast_day)  # add the fetch/cache data to the list of dictionaries
            return content_after_k
        else:
            return None

    def get_all(self):
        """ return freshly fetched or cached content """
        if self._request_allowed():
            # return the fetched data from the API
            return self._fetch_data()
        else:
            # return the cache data from the last successful API fetch. Could be None if never successful.
            return self._read_buffer()

    def _fetch_data(self):
        """ json encoded response from webservice .. or none """
        try:
            response = requests.get(self.props['service_url'] % (self.props['apikey'], self.props['lat'],
                                                                 self.props['lon'], self.props['days']))
            self.props['last_used'] = int(time.time())  # store the last time we fetch
            self._save_settings()  # remember time of the last service request
            if response.status_code == 200:  # this is a success response code from the API
                content = self._create_content(response.json())
                logging.info("successfully requested new content")
                self._write_buffer(content)  # remember last service request(s) results.
            else:
                logging.warning("response: {} {} {}".format(response.status_code, response, response.text))
                content = None
        except (HTTPError, Timeout, ConnectionError, ValueError) as e:
            logging.error("except: " + str(e))
            content = None
        return content

    def _create_content(self, ws_json):
        """ from the list of dictionary json response, add to the dictionary the 'k', 'caption', and 'summary' """
        for record in ws_json:
            record['k'] = record['date']  # reuse the date as the unique 'k' because it is always unique
            record['caption'] = time.strftime('%Y-%m-%d', time.localtime(record['date'])) + \
                                ' | UV Index: ' + str(record['value'])
            record['summary'] = str(self.props['days']) + ' day UV Index forecast for the GCCD local community. ' \
                                                          'UV Index ranges from 1 to 11+ (low to extreme). If you ' \
                                                          'would like to know more about UV Indexes please visit: ' \
                                                          'https://www.epa.gov/sunsafety/uv-index-scale-1 '
            record['img'] = 'https://www.epa.gov/sites/production/files/sunwise/images/uviscaleh_lg.gif'

        return ws_json  # The response is already a list of dictionaries where each dictionary is a day in the forecast


if __name__ == "__main__":
    """ starting the app! """
    sensor = UVIndex()
    current_content = sensor.get_all()
    print("Here are the " + str(sensor.props['days']) + " day forecast of the UV Index for Grossmont College:")
    for a in current_content:
        print(a)

    # Sensor will run indefinitely until a KeyboardInterrupt (Ctrl + c) to stop the sensor
    while True:
        try:
            # current time in epoch seconds. Used to prevent Service calls from overstepping their limits
            time_now = int(time.time())

            if sensor.has_updates(time_now):
                new_content_from_now = sensor.get_content(time_now)  # list of dictionary forecasts of UV Index from now
                print('The following are your new UV Index forecast:')
                if new_content_from_now is not None and len(new_content_from_now) > 0:
                    for new_content in new_content_from_now:
                        print(new_content)  # display to user what has happened so they get feedback from Sensor
                else:
                    not_found = 'New forecast not found. Server may be down. Try again later.'
                    logging.error(not_found)  # keep a log of this event
                    print(not_found)  # display to user what has happened so they get feedback from Sensor
            else:
                logging.info('UV Index Sensor is sleeping for 30 seconds. Then wakes up to check if it has waited '
                             'long enough to then fetch data.')  # keep a log of this event
                time.sleep(30)  # sleep for 30 seconds so that the loop does not consume and waste processes
        except KeyboardInterrupt:  # Ctrl + c to stop the sensor if ran from this file.
            logging.info("UV Index Sensor stopped.")
            break
