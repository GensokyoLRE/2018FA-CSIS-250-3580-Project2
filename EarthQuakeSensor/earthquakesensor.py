"""
EarthQuakeSensor fetches data from the USGS earthquake API the gathered data is formatted and images of earthquake
location are gathered though MapView API via longitude and latitude of each earthquake location and data is submitted
is finally submitted to the GhostCMS API
"""
import os
import json
import time
import logging
import datetime
import requests
from sensor import SensorX


logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.getcwd(), 'logs', 'sensor.log'),
    filemode='a',
    format='%(asctime)s - %(lineno)d - %(message)s'
)


class EarthQuakeSensor(SensorX):
    """
    Sensor receives data from USGS for EarthQuake or disaster event types
    for a specific location or entire country
    """

    def __init__(self):
        """ read sensor settings from config file """
        super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))

    # def has_updates(self):
    #     """
    #     find out if there is new data and return
    #     true or false if new data was found
    #     """
    #     try:
    #         get_content = self.get_all()
    #         read_content = self._read_buffer()
    #         if len(get_content) > len(read_content):
    #             return True
    #         else:
    #             return False
    #     except (TypeError, Exception) as ex:
    #         logging.error(f"Error checking updates exception: {ex}")

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
        """ return content after k"""
        content = self.get_all()
        return content[k] if content else None

    def get_featured_image(self):
        pass

    def get_all(self):
        """ Return fresh or cached content """
        if self._request_allowed():
            print("Getting New")
            return self._fetch_data()
        else:
            print("Getting Old")
            return self._read_buffer()

    def _fetch_data(self):
        """
        Json encoded response from API is fetched and used in _create_content
        and written with _write_buffer
        """
        try:
            logging.info("Fetching from API...")

            params = {
                'starttime': self.props.get('starttime'),
                'endtime': datetime.datetime.now().isoformat(),
                'minlongitude': self.props.get('minlongitude'),
                'maxlongitude': self.props.get('maxlongitude'),
                'minlatitude': self.props.get('minlatitude'),
                'maxlatitude': self.props.get('maxlatitude'),
                'minmagnitude': self.props.get('minmagnitude'),
                'maxmagnitude': self.props.get('maxmagnitude'),
                'eventtype': self.props.get('eventtype')
            }

            response = requests.get(self.props.get('service_url'), params=params, timeout=self.props['request_timeout'])
            if response.status_code == requests.codes.ok:
                self.props['last_used'] = int(time.time())
                self._save_settings()
                response_content = json.loads(response.content)
                create_content = self._create_content(response_content)
                self._write_buffer(create_content)

                return create_content
            else:
                logging.warning(f"Response Status: {response.status_code} {response.text}")
        except (requests.HTTPError, requests.Timeout, requests.ConnectionError, ValueError) as ex:
            logging.error(f"Error encountered exception: {ex}")

    def _map_view(self, longitude, latitude):
        try:
            logging.info("Fetching map image from API")
            params = {
                'app_id': self.props.get('map_app_id'),
                'app_code': self.props.get('map_app_code'),
                't': self.props.get('map_terrain_type'),
                'c': "{},{}".format(longitude, latitude)
            }
            response = requests.get(self.props.get('map_service_url'), params=params)
            if response.status_code == requests.codes.ok:
                response_image = response.url
            else:
                logging.warning(f"Response Status: {response.status_code} {response.text}")
                response_image = None

            return response_image
        except (requests.HTTPError, requests.Timeout, requests.ConnectionError, ValueError) as ex:
            logging.error(f"Error encountered exception: {ex}")

    def _create_content(self, json_f):
        """ Convert the earth quake data into something more readable """
        """ 
        'k'       : 0  a unique records identifier
        'date'    : string representation of datetime.datetime
        'caption' : 'Grossmont–Cuyamaca Community College District'
        'summary' : 'Grossmont–Cuyamaca Community College District is a California community college district'
        'story'   : (optional, either plaintext or markdown) 'The Grossmont–Cuyamaca Community College District is ..'
        'img'     : (optional link to a jpg or png) 'https://upload.wikimedia.org/wikipedia/.../logo.png'
        'origin'  : (optional link to the source) 'https://en.wikipedia.org/wiki/...'
               """

        content = []
        json_content = json_f['features']
        for i in range(len(json_content)):
            json_content = json_f['features'][i]
            json_content_prop = json_content['properties']

            post = {
                'k': json_content.get('id', '0'),
                'date': json_content_prop.get('time'),
                'caption': json_content_prop['title'],
                'summary': '----EarthQuake details----\n'
                           'Location: {}\n'
                           'Magnitude: {}'.format(json_content_prop['place'].split('of')[1], json_content_prop['mag']),
                'story': '',
                'img': self._map_view(json_content['geometry']['coordinates'][0], json_content['geometry']['coordinates'][1])
            }
            content.append(post)
        # print(post)
        # print(content)
        return content


if __name__ == "__main__":
    earthquake = EarthQuakeSensor()
    print("Fetching latest earthquakes..")
    content = earthquake.get_all()
    print(content)

    count = 0
    while True:
        if count > 20:
            break
        else:
            count += 1
            if earthquake.has_updates():
                time.sleep(20)
                print("Fetching updates...")
                updates = earthquake.get_content(2)
                content_update = earthquake.get_content(3)
