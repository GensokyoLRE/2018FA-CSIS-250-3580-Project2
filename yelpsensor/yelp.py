""" A Software Sensor using Yelp's API """
import os
import time
import logging
import requests
from requests import Timeout, HTTPError, ConnectionError
from sensor import SensorX
import pprint
import json

# logging into current_dir/logs/{sensor_name}.log
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.getcwd(), 'logs', 'yelp.log'),
    filemode='a',
    format='%(asctime)s - %(lineno)d - %(message)s')


class Yelp(SensorX):
    """ Uses Yelp's search API to get a list of restaurants in an area.
    Generates a report with details about restaurants that would likely appeal to students."""

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
            request = requests.request('GET', self.props['URL'], headers=self.props['headers'], params=self.props['parameters'])
            print("\nSearching... ", request.url, "\n")
            response = request.json().get('businesses')
            self.props['last_used'] = int(time.time())
            self._save_settings()  # remember time of the last service request
            if request.status_code == 200:
                content = self._create_content(response)
                logging.info("successfully requested new content")
                self._write_buffer(content)  # remember last service request(s) results.
            else:
                logging.warning("response: {} {} {}".format(request.status_code, request, request.text))
                print("response: {} {} {}".format(request.status_code, request, request.text))
                content = None
        except (HTTPError, Timeout, ConnectionError, KeyError, ValueError, TypeError) as e:
            logging.error("except: " + str(e))
            print("except: " + str(e))
            content = None
        return content

    def get_featured_image(self):
        return self.props['featured_image']

    @staticmethod
    def _create_content(ws_json):
        """ Filter results to find cheap, open restaurants with pickup or delivery options. Format this information
        to fit our needs."""
        len_businesses = len(ws_json)
        # pop out the data we don't need
        for x in range(len_businesses - 1, -1, -1):
            try:
                if ws_json[x]['is_closed'] is True or len(ws_json[x]['price']) > 1 \
                        or ('delivery' or 'pickup') not in ws_json[x]['transactions']:
                    ws_json.pop(x)
            except:
                ws_json.pop(x)
        bus_final = []
        for item in ws_json:   # select the fields we need out of the json and store it in a dictionary
            filtered_dict = {k: v for (k, v) in item.items() if 'name' in k or 'categories' in k
                             or 'location' in k or 'display_phone' in k or 'url' in k or 'image_url' in k
                             or 'transactions' in k or 'id' in k}
            # parse the address, transaction, and description data
            address = filtered_dict['location']['display_address']
            filtered_dict['location'] = ", ".join(address)
            transactions = filtered_dict['transactions']
            filtered_dict['transactions'] = ", ".join(transactions)
            description = [list(d.values()) for d in filtered_dict['categories']]
            for x in range(len(description)): description[0].extend(description[x])
            description_str = (" ".join(description[0])).lower().replace(" & ", "_")
            filtered_dict['categories'] = ", ".join(list(set(description_str.split(" "))))
            filtered_dict['k']= filtered_dict['id']
            filtered_dict['date']= filtered_dict['image_url']
            filtered_dict['caption']= filtered_dict['name']
            filtered_dict['summary']= "{} : {} : {}".format(filtered_dict['location'], filtered_dict['transactions'], filtered_dict['categories'])
            filtered_dict['img']= filtered_dict['image_url']
            filtered_dict['origin']= filtered_dict['url']


            bus_final.append(filtered_dict)
        logging.info("Searched " + str(len_businesses) + " restaurants for a result of "
                     + str(len(bus_final)) + " that match our criteria.")
        print("Success!")
        return bus_final


if __name__ == "__main__":
    """ let's play """
    sensor = Yelp()
    # with open('results_final.json', 'w') as f:
    #     json.dump(sensor.get_all(), f, indent=2, sort_keys=True)
    for d in sensor.get_all():
        for key in d.keys():
            print("{} : {}".format(key, d.get(key)))
