"""
A Sensor to retrieve a list of animals available for adoption at
the El Cajon Animal Shelter as a list of pet dictionaries using the PetFinder API
"""

__version__ = "1.1"
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

__LOG_DIRECTORY = 'petfinderlog'
__LOG_FILENAME = 'petfinder.logs'

# Create the logs directory if it doesn't already exist
try:
    os.makedirs(os.path.join(os.path.dirname(__file__), __LOG_DIRECTORY))
except OSError as e:
    if e.errno != errno.EEXIST:
        print("Error is: " + str(e))

# Create standard logging entries
# info for status messages
# warning for errors that will cause the usage of cached data
# critical for errors that prevent the running of the sensor
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.path.dirname(__file__), __LOG_DIRECTORY, __LOG_FILENAME),
    filemode='a',
    format='%(asctime)s - %(lineno)d - %(levelname)s - %(message)s')


class PetFinderSensor(SensorX):
    """
    Uses API from petfinder.com to create a list of dictionaries for each pet available for adoption

    Will used cached data if petfinder.com is not available, or returns an invalid response
    """

    logging.info("\n")  # Add a new line in logs to start run

    def __init__(self):
        """ Create new PetFinderSensor object and read sensor settings from config file """
        try:
            super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))
        except (Exception, OSError, ValueError) as e:
            logging.critical("Not able to read CONFIG_FILE " + self.__class__.__name__ + '.json')
            logging.critical("Error was: " + str(e))
            exit()

    def has_updates(self, k):
        """
        k doesn't matter.  Need to check if animal lastUpdated is greater than PetFinderSensor last_has_update

        Returns value of 1 if any animals found with newer date than last check for updates
        """
        update_available = 0
        if self._request_allowed():
            has_update = self.get_all()
            for update_pet in has_update:
                if datetime.strptime(update_pet['k'], "%Y-%m-%d"'T'"%H:%M:%S"'Z') > datetime.fromtimestamp(self.props['last_used']):
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
        time.sleep(11)  # Since the has_updates ran a get_all it updated the last_used time
        if self._request_allowed():
            logging.info("get_content _request_allowed passed")
            content = self.get_all()  # Returns all pets with only the data we're looking for
            for pet in content:
                if datetime.strptime(pet['k'], "%Y-%m-%d"'T'"%H:%M:%S"'Z') > datetime.fromtimestamp(self.props['last_used']):
                    newContent.append(pet)
            self.props['last_used'] = int(time.time())
            try:
                self._save_settings()  # Saves that a request has been made to the service
                logging.info("Saved last_has_update from get_content")
            except (Exception, OSError, ValueError) as e:
                logging.warning("Unable to save JSON settings : " + str(e))

        else:
            logging.info("get_content _request_allowed not passed")
        return newContent

    def get_all(self):
        """
        Request information on all animals available for adoption

        Saves a copy of response.txt data to be used for cached requests

        Returns a list of dictionaries for all pets
        """
        if self._request_allowed():
            url = self.props['service_url']+"%s?key=%s&count=%d&id=%s&format=%s"
            try:
                response = requests.get(url % (self.props['service_method'], self.props['key'], self.props['return_count'], self.props['shelter_id'], self.props['format']))
            except (requests.ConnectionError, requests.ConnectTimeout) as e:
                logging.warning("HTTP Request failed for: " + str(e))
            self.props['last_used'] = int(time.time())
            try:
                self._save_settings()  # Saves that a request has been made to the service
                logging.info("Settings saved in get_all")
            except (Exception, OSError, ValueError) as e:
                logging.warning("Unable to save JSON settings : " + str(e))
            try:
                # URL should return JSON, if not, something went wrong
                response_json = json.loads(response.text)
                logging.info("The response from %s was JSON" % (self.props['service_url']))
            except (Exception, OSError, ValueError) as e:
                # The data we received from the response was not in JSON
                # Something went wrong, so load the saved data
                logging.warning("The response from %s was not JSON" % (self.props['service_url']))
                response = self._read_buffer()
                return self._create_record(json.loads(response))
            if response is not None and response.status_code == 200:
                self._write_buffer(response.text)
                return self._create_record(response_json)
            else:
                logging.warning("The response was bad, using saved data")
                response = self._read_buffer()
                return self._create_record(json.loads(response))
        else:
            logging.info("The request was not allowed, using saved data")
            response = self._read_buffer()
            return self._create_record(json.loads(response))

    @staticmethod
    def _create_record(d):
        """
        Create a list of dictionaries with details about each pet available from the shelter

        Returns a dictionary list of pets with selected fields of:
            k -- lastUpdate of Pet within PetFinder

            caption -- name of Pet

            summary -- Age, Sex, Pet Type (Dog, Cat, etc), Breed, PetFinderID

            story -- description of Pet

            img -- large picture of Pet

            origin -- location on PetFinder website to see Pet
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
            caption = d['petfinder']['pets']['pet'][pet]['name']['$t']
            # https://www.petfinder.com/search/pets-for-adoption/?name=stanley&shelter_id[0]=CA141
            origin = "https://www.petfinder.com/search/pets-for-adoption/?name=" + str.lower(caption) + \
                        "&shelter_id[0]=" + d['petfinder']['pets']['pet'][pet]['shelterId']['$t']
            record.append({'k': d['petfinder']['pets']['pet'][pet]['lastUpdate']['$t'],
                           'caption': caption,
                           'summary': summary,
                           'story': story,
                           'img': use_this_photo,
                           'origin': origin
                          })
        logging.info("Completed _create_record")
        return record


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
