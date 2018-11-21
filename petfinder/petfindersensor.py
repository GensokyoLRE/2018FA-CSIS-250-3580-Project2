"""
A Sensor to retrieve a list of animals available for adoption at
the El Cajon Animal Shelter using the PetFinder API
"""

__version__ = "1.2"
__author__ = "Roger Hinson"
__email__ = "roger.hinson@gmail.com"

from sensor import SensorX
import json
import os
import time
import requests
import logging
import errno
import re
from datetime import datetime


class PetFinderSensor(SensorX):

    __LOG_DIRECTORY = 'petfinderlog'
    __LOG_FILENAME = 'petfinder.log'
    __SAVED_RECORDS = 'petfinder_saved_records.json'

    # Create the logs directory if it doesn't already exist
    try:
        os.makedirs(os.path.join(os.path.dirname(__file__), __LOG_DIRECTORY))
    except OSError as e:
        if e.errno != errno.EEXIST:
            print("Error is: " + str(e))

    # Create standard logging entries
    logging.basicConfig(
        level=logging.INFO,
        filename=os.path.join(os.path.dirname(__file__), __LOG_DIRECTORY, __LOG_FILENAME),
        filemode='a',
        format='%(asctime)s - %(lineno)d - %(levelname)s - %(message)s')

    logging.info("\n")  # Add a new line in log to start run

    def __init__(self):
        """ Create new PetFinderSensor object and read sensor settings from config file """
        super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))

        # try:
        #     with open(os.path.join(os.path.dirname(__file__)) + "/" + PetFinderSensor.__CONFIG_FILE) as json_text:
        #         self.props = json.load(json_text)
        #     logging.info("This sensor just woke up .. ready to call " + self.props['service_url'])
        # except (Exception, OSError, ValueError) as e:
        #     logging.critical("Not able to read __CONFIG_FILE " + PetFinderSensor.__CONFIG_FILE)
        #     logging.critical("Error was: " + str(e))
        #     exit()

    def has_updates(self, k):
        """
        k doesn't matter.  Need to check if animal lastUpdated is greater than PetFinderSensor last_has_update

        Returns value of 1 if any animals found with newer date than last check for updates
        """
        update_available = 0
        if self._request_allowed():
            has_update = self.get_all()
            for update_pet in has_update:
                if datetime.strptime(update_pet['k'], "%Y-%m-%d"'T'"%H:%M:%S"'Z') > datetime.fromtimestamp(self.props['last_has_update']):
                    update_available = 1
                    logging.info("Updates are available")
                    return update_available
            if update_available == 0:
                logging.info("Updates are not available")
                return 0
        else:
            return 0

    def get_content(self, k):
        """
        k doesn't matter.  Need to check if animal lastUpdated is greater than PetFinderSensor last_has_update

        Returns a list of dictionaries for each updated pet
        """
        newContent = []
        time.sleep(11)  # Since the has_updates ran a get_all it updated the last_get_all time
        if self._request_allowed():
            content = self.get_all()  # Returns all pets with only the data we're looking for
            for pet in content:
                if datetime.strptime(pet['k'], "%Y-%m-%d"'T'"%H:%M:%S"'Z') > datetime.fromtimestamp(self.props['last_has_update']):
                    newContent.append(pet)
            self.props['last_has_update'] = int(time.time())
            self._save_settings()  # Saves that a request has been made to the service
            logging.info("Saved last_has_update from get_content")
        else:
            logging.info("get_content did not allow _request_allowed")
        return newContent

    def get_all(self):
        """
        Request information on all animals available for adoption

        Saves a copy of response.txt data to be used for cached requests

        Returns a list of dictionaries for all pets
        """
        if self._request_allowed():
            url = self.props['service_url'] + "%s?key=%s&count=%d&id=%s&format=%s"
            try:
                response = requests.get(url % (self.props['service_method'], self.props['key'], self.props['return_count'], self.props['shelter_id'], self.props['format']))
            except (requests.ConnectionError, requests.ConnectTimeout) as e:
                logging.warning("HTTP Request failed for: " + str(e))
            self.props['last_get_all'] = int(time.time())
            self._save_settings()  # Saves that a request has been made to the service
            logging.info("Settings saved in get_all")
            try:
                # URL should return JSON, if not, something went wrong
                response_json = json.loads(response.text)
                logging.info("The response from %s was JSON" % (self.props['service_url']))
            except (Exception, OSError, ValueError) as e:
                # The data we received from the response was not in JSON
                # Something went wrong, so load the saved data
                logging.warning("The response from %s was not JSON" % (self.props['service_url']))
                response = self._read_saved_data()
                return self._create_record(json.loads(response))
            if response is not None and response.status_code == 200:
                try:
                    with open(os.path.join(os.path.dirname(__file__)) + "/" + PetFinderSensor.__SAVED_RECORDS, 'w') as backup:
                        backup.write(response.text)
                        logging.info("Saved response from %s" % (self.props['service_url']))
                except (Exception, OSError, ValueError) as e:
                    logging.warning("File response write failed: " + str(e))
                finally:
                    return self._create_record(response_json)
            else:
                logging.warning("The response was bad, using saved data")
                response = self._read_saved_data()
                return self._create_record(json.loads(response))
        else:
            logging.warning("The request was not allowed, using saved data")
            response = self._read_saved_data()
            return self._create_record(json.loads(response))

    @staticmethod
    def _create_record(d):
        """
        Create a list of dictionaries with details about each pet available from the shelter

        Returns a dictionary list of pets with selected fields
        """
        record = []
        for pet in range(len(d['petfinder']['pets']['pet'])):
            # Find large sized photo and just use the first one
            for photo in range(len(d['petfinder']['pets']['pet'][pet]['media']['photos']['photo'])):
                if d['petfinder']['pets']['pet'][pet]['media']['photos']['photo'][photo]['@size'] == 'x':
                    use_this_photo = d['petfinder']['pets']['pet'][pet]['media']['photos']['photo'][photo]['$t']
                    break
            # The JSON format is different if there's more than one breed type
            if 1 == len(d['petfinder']['pets']['pet'][pet]['breeds']['breed']):
                breed = d['petfinder']['pets']['pet'][pet]['breeds']['breed']['$t']
            else:
                for breeds in range(len(d['petfinder']['pets']['pet'][pet]['breeds']['breed'])):
                    if breeds == 0:
                        breed = d['petfinder']['pets']['pet'][pet]['breeds']['breed'][breeds]['$t']
                    else:
                        breed = breed + " / " + d['petfinder']['pets']['pet'][pet]['breeds']['breed'][breeds]['$t']
                    if (breeds > 0) and breeds == len(d['petfinder']['pets']['pet'][pet]['breeds']['breed']) - 1:
                        breed = breed + " Mix"
            # Create a summary with some pet attributes
            summary = d['petfinder']['pets']['pet'][pet]['age']['$t'] + " " + \
                      d['petfinder']['pets']['pet'][pet]['sex']['$t'] + " " + \
                      d['petfinder']['pets']['pet'][pet]['animal']['$t'] + " " + \
                      breed + "\n" + \
                      "PetFinder ID: " + d['petfinder']['pets']['pet'][pet]['id']['$t']
            # Make all UPPERCASE words BOLD with markdown, word is two or more adjacent UPPERCASE characters
            story = re.sub(r'\b([A-Z][A-Z]+)\b', r'**\1**',
                           d['petfinder']['pets']['pet'][pet]['description']['$t'])
            record.append({'k': d['petfinder']['pets']['pet'][pet]['lastUpdate']['$t'],
                           'caption': d['petfinder']['pets']['pet'][pet]['name']['$t'],
                           'summary': summary,
                           'story': story,
                           'img': use_this_photo
                          })
        logging.info("Completed _create_record")
        return record

    def _request_allowed(self):
        # This use to capture the real allowance of 10,000 times per day
        # Simplified to new variation for easier grading  :)
        return not self.props['offline_mode'] and (int(time.time()) - self.props['last_get_all']) > self.props['update_frequency']

    def _save_settings(self):
        # Save JSON settings to config file
        try:
            with open(os.path.join(os.path.dirname(__file__), PetFinderSensor.__CONFIG_FILE), 'w') as outfile:
                json.dump(self.props, outfile)
        except (Exception, OSError, ValueError) as e:
            logging.warning("Unable to save JSON settings : " + str(e))

    def _read_saved_data(self):
        # Read saved response.text data from saved file in case URL can't be accessed
        try:
            with open(PetFinderSensor.__SAVED_RECORDS) as saved_data:
                response = saved_data.read()
                logging.info("Read response from saved file")
            return response
        except (Exception, OSError, ValueError) as e:
            logging.critical("Reading saved data error is: " + str(e))
            return None


if __name__ == "__main__":
    sr = PetFinderSensor()
    print("This is me : " + str(sr))
    print("let's go ..")
    json_doc = sr.get_all()
    print(json_doc)

    print("\n")

    for pet in json_doc:
        print(pet)

    print("\nChecking for Pet Updates\n")

    time.sleep(11)  # Need to wait 10 seconds before getting an update

    if sr.has_updates(datetime.now()):
        json_doc = sr.get_content(datetime.now())
        for pet in json_doc:
            print(pet)
