"""
GoogleSensor.py
Author: Michael Hall

This sensor pulls xml data from the Google Places API.
limit for requests is defined by me (based on money) so don't call this too much.
This sensor pulls a list of restaurants, caches the list and outputs a random restaurant

Please only run this once every 20 minutes (1200 seconds). If you call this more than once every 20 minutes it will output the same "random" restaurant to your page.
This 20 minute limit can be changed within the conf file "outputDelta"

"""
import mimetypes
import os
import pathlib
import logging
import json
import time
import requests
from datetime import datetime
from publisher.publisher import Publisher
from sensor import SensorX

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'GoogleSensor.json')
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'GoogleCache.json')
OUTPUT_CACHE_FILE = os.path.join(os.path.dirname(__file__), 'OutputGoogleCache.json')


class GoogleSensor(SensorX):

    def __init__(self):
        super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))
        """ read sensor settings from config file """
        self.__settings = self.props
        logging.info("Sensor just woke up .. ready to be called")

    def get__settings(self):
        return self.__settings

    def has_updates(self, k):
        return True

    def get_all(self):
        my_list = []
        for i in range(self.__settings['dump_size']):
            my_list.extend(self.content())
        return my_list

    def get_featured_image(self):
        """
        needs to be overridden if inheriting from SensorX provides a featured image
        Left this in here as an easter egg, The change to the theme broke my monkey but fixed my html, Thanks professor
        """
        return "monkey.jpg"

    def get_content(self, k):
        """ return content after k"""
        content = self.get_all()
        return content if 0 < len(content) and content[0]['k'] != k else None

    def content(self):

        """Gets content from the files, outputs content as a list for publishing to Ghost
            Use this one Professor Paulus, it'll give you your list of 1 dictionary.
        """

        # Variables used for preventing generating restaurants too much
        currentOutCallTime = int(time.time())
        previousOutCallTime = int(self.__settings.get('output_last_call'))
        outDelta = currentOutCallTime - previousOutCallTime
        outRequestDelta = self.__settings.get('outputDelta')

        # if, else statement used to prevent generating restaurants too much
        if outDelta >= outRequestDelta:
            # Sets the value of debug and "r" (return) to null
            # This helps with returning debug messages
            self.debug = ""
            self.r = ""

            self.offline = self.props.get('offline_mode')
            self.debugMode = self.props.get('debug_mode')

            # Main if statement, if offline is set to true on config file, run offline function
            # else: run the online function to pull info from the Web API
            if self.offline in ["true", "True", "T", "t"]:
                self.call_WebAPI_offline()
            else:
                self.call_WebAPI()

            # Formats the output (assignes attributes to this class)
            self.outFormat()

            # Dictionary Output for GHOST CMS
            ts0 = datetime.now()
            outList = [{
                'k': str(ts0),
                'date': ts0.strftime('%Y-%m-%d %I:%M:%S %p'),
                'caption': f'Places to eat around Grossmont College: {self.restaurantName}',
                'summary': self.restaurantName,
                'story': f'{self.htmlOut}',
                'img': f'{self.image}'
            }]

            # Saves the outList as a cache file (to prevent generating a new restaurant too frequently (cuts down on the cost)
            with open(OUTPUT_CACHE_FILE, 'w') as outputCacheFile:
                outputCacheFile.write(json.dumps(outList, indent=4))
            # Saves the output_last_call time to limit generating new restaurants too frequently
            self.__settings['output_last_call'] = str(int(time.time()))
            # Overwrite old JSON config file with new timestamp
            with open(CONFIG_FILE, 'w') as backup:
                backup.write(json.dumps(self.__settings, indent=4))
        else:
            # Pulls from old cache file
            with open(OUTPUT_CACHE_FILE, 'r') as outputCacheFile:
                outList = json.load(outputCacheFile)

        return outList

    def call_WebAPI_offline(self):
        """
        This calls for the cached file
        I just call this function "call_WebAPI_offline" so it has a similar name to "Call_WebAPI"
        """
        try:
            logging.info("Sensor offline, pulling from cache")
            with open(CACHE_FILE, "r") as jsonIn:
                self.r = json.load(jsonIn)
        except:
            logging.info("Error, GoogleCache.json file may be missing")

    def call_WebAPI(self):
        """
        calls the webAPI, creates a cache file. if there is an error then it pulls info from the Cache
        :return:
        """
        try:
            # Protection from issuing too many requests
            currentCallTime = int(time.time())
            previousCallTime = int(self.__settings.get('last_call'))
            delta = currentCallTime - previousCallTime
            requestDelta = self.__settings.get('request_delta')
            # Todo: 5 needs to be replaced with self.__settings.get('request_delta')
            if delta > requestDelta:
                # Request data file from api
                logging.info("API Call Successful, Pulling from WebAPI")
                # This adds the json api call output to the attribute "self.r"
                self.r = requests.get(self.__settings.get('service_url') % (self.__settings.get('key'))).text
                # with open(CACHE_FILE, "r") as jsonIn:
                #    self.r = jsonIn.read()
                with open(CACHE_FILE, "w") as jsonOut:
                    jsonOut.write(self.r)
                # Set last call time (str(int(time.time())) removes decimal notation from the seconds output
                with open(CACHE_FILE, "r") as jsonIn:
                    self.r = json.load(jsonIn)
                self.__settings['last_call'] = str(int(time.time()))
                # Overwrite old JSON config file with new timestamp
                with open(CONFIG_FILE, 'w') as backup:
                    backup.write(json.dumps(self.__settings, indent=4))
            else:
                logging.info("Called api too fast, request denied by internal safeguards, Pulling from Cache")
                # Read from cache
                with open(CACHE_FILE, "r") as jsonIn:
                    self.r = json.load(jsonIn)
        except:
            logging.info("Errored out")
            self.call_WebAPI_offline()

    def outFormat(self):
        """
        This function formats and returns the output to the website in an HTML format
        """

        # Pseudo Random Numbers: For choosing a restaurant to display at "random"
        # Source: http://farside.ph.utexas.edu/teaching/329/lectures/node107.html#e71
        # But it was reinterpreted in my own hacky (and probably insecure) way. Used the Linear congruental method (which as mentioned can have issues with integers overflowing)
        # c = int(str(int(time.time())[-2]) * int(str(int(time.time())[-1]))
        with open(CONFIG_FILE, 'r') as confFile:
            seed = int(str(time.time())[-1]) + hash(str(self.r)) - int(str(hash(confFile))[1:5])
        rand = lambda maxNum: (69 * abs(seed) + 42) % maxNum

        # Choose a random restaurant from the list in "self.r"
        restaurant = self.r['results'][rand(len(self.r['results']))]
        try:
            embedMap = "<iframe style='width:95%;height:25%;' src=" + str(self.__settings.get('mapsEmbedURL') % (
            self.__settings.get('key'), restaurant['place_id'])) + "></iframe>"
        except:
            embedMap = "<h2 style='color:red'> An Error Has Occurred with the embedded map generation </h2>"

        # embedMap = "test"

        self.restaurantName = restaurant['name']

        # removeMaxWidth = '<style>window.onload = function () {document.GetElementByID("main").style.color. = "red";};</style>'

        # Output restaurant as HTML
        self.htmlOut = f"""<div id=details style='display:flex;flex-flow:row wrap;justify-content:space-around;background-color:azure;border:solid 1px green;'>\
        <h2 style="flex:100%;text-align: center;;padding:20px;background-color:skyblue;margin-top:0px;">Places to eat around Grossmont College</h2>\
            <div id=column1 style='flex:30%;padding-right;10px;padding-left:10px;'>\
                <h1>{restaurant['name']}</h1>\
                <p>Address: {restaurant['vicinity']}</p>\
                <p>Rating: {restaurant['rating']}</p>\
            </div>\
            <div id=map style='flex:65%;height:100%;'>\
                <h2>Map:</h2>\
                {embedMap}\
            </div>\
        </div>"""

        try:
            url = str(self.__settings.get('photoEmbedURL') % (
            restaurant['photos'][0]['photo_reference'], self.__settings.get('key')))
            response = requests.get(url)
            if response.status_code == 200:
                extension = mimetypes.guess_extension(response.headers['content-type']).replace('jpe', 'jpg')
                img_path = os.path.join(os.path.dirname(__file__), restaurant['place_id'] + extension)
                with open(img_path, 'wb') as img:
                    img.write(response.content)
                self.image = pathlib.Path(img_path)
            else:
                self.image = None
        except:
            self.image = None
