"""
A consumer for GCCCD Software Sensors, takes content from sensors and publishes into Ghost
"""

__version__ = "2.0"
__author__ = "Wolf Paulus"
__email__ = "wolf.paulus@gcccd.edu"

import logging
import os
import json
import requests
import time
from threading import Thread
from ghost_client import Ghost, GhostException
from instasensor.instasensor import InstaSensor
from foosensor.foosensor import FooSensor
from openweathersensor.openweather import OpenWeather

logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(os.getcwd(), 'logs', 'publisher.log'),
    filemode='a',
    format='%(asctime)s - %(lineno)d - %(message)s')


# noinspection PyMethodMayBeStatic
class Publisher:
    """ requires external lib to access Ghost server: ghost-client (v0.0.4)  """
    __ghost = None

    def __init__(self):
        if Publisher.__ghost is None:
            try:
                Publisher.__ghost = Publisher.__connect()
            except GhostException as e:
                logging.error(str(e))

    @staticmethod
    def __upload_img(img_path):
        img = ''
        if img_path is not None:
            try:
                img_name = os.path.basename(img_path)
                response = requests.get(img_path, stream=True)
                img = Publisher.__ghost.upload(name=img_name, data=response.raw.read())
            except (GhostException, requests.exceptions) as e:  # todo: do we need a broader catch here?
                logging.error(str(e))
        return img

    def publish(self, sensor, **kwargs):
        # find or create a sensor name
        name = sensor.__class__.__name__
        if not kwargs.get('k') or not kwargs.get('caption') or not kwargs.get('summary'):
            logging.info("Incomplete record, won't be published " + name)
            return
        try:
            # re-use or create a tag
            tags = Publisher.__ghost.tags.list(fields='name,id')
            ids = [t['id'] for t in tags if t['name'] == name]
            tag = Publisher.__ghost.tags.get(ids[0]) if 0 < len(ids) else \
                Publisher.__ghost.tags.create(name=name, feature_image=sensor.get_featured_image())
            # re-use summery as story, if necessary
            if not kwargs.get('story'):
                kwargs['story'] = kwargs.get('summary')
            # load and publish referenced image
            img = Publisher.__upload_img(kwargs.get('img', None))
            # look for a link to the original source
            if kwargs.get('origin'):
                kwargs['story'] = kwargs.get('story') + '\n\n[Original Source](' + str(kwargs.get('origin')) + ')'
            # create a post
            Publisher.__ghost.posts.create(
                title=str(kwargs.get('caption')[:255]),  # up to 255 allowed
                custom_excerpt=str(kwargs.get('summary')),  # todo is there a size limit ?
                markdown=kwargs.get('story'),  # todo is there a size limit ?
                tags=[tag],
                feature_image=img,
                status='published',
                featured=False,
                page=False,
                locale='en_US',
                visibility='public'
                # slug='my custom-slug',
            )
        except GhostException as e:
            logging.error(str(e))

    def delete_posts(self, sensor):
        """ delete all posts that have the provided  tag"""
        tag = sensor.__class__.__name__
        try:
            posts = Publisher.__ghost.posts.list(status='all', include='tags')
            ids = []
            for _ in range(posts.pages):
                last, posts = posts, posts.next_page()
                for p in last:
                    if p['tags'] and p['tags'][0]['name'] == tag:  # todo what if more than one tag is used
                        ids.append(p.id)
                if not posts:
                    break
            for i in ids:
                Publisher.__ghost.posts.delete(i)
        except GhostException as e:
            logging.error(str(e))

    @staticmethod
    def __connect():
        """ ghost allows 'only;' 100 logins per hour from a single IP Address ..."""
        try:
            with open(os.path.join(os.path.dirname(__file__), 'publisher.json')) as json_text:
                settings = json.load(json_text)
            ghost = Ghost(settings['server'], client_id=settings['client_id'], client_secret=settings['client_secret'])
            ghost.login(settings['user'], settings['password'])
            return ghost
        except GhostException as e:
            logging.error(str(e))
            return None


class SmartSensor(Thread):
    running = True

    def __init__(self, sensor, delete_old=False):
        super().__init__(name=sensor.__class__.__name__)
        self.sensor = sensor
        self.k = 0
        if delete_old:
            Publisher().delete_posts(self.sensor)  # delete current content on (re-)start
        for s in self.sensor.get_all():
            Publisher().publish(self.sensor, **s)
            self.k = s['k']

    def run(self):
        print(self.name + " is running now")
        while SmartSensor.running:
            if self.sensor.has_updates(self.k):
                for s in self.sensor.get_content(self.k):
                    Publisher().publish(self.sensor, **s)
                    self.k = s['k']
            time.sleep(5)
        print(self.name + " ended")


if __name__ == "__main__":
    # GHOST 'Only 100 request per IP address per hour!!
    # ghost_client import Ghost -->  https://github.com/rycus86/ghost-client
    # look for client_id and client_id in the html code here: http://localhost:2368

    SmartSensor(InstaSensor()).start()
    SmartSensor(FooSensor(), True).start()
    SmartSensor(OpenWeather(), True).start()
    time.sleep(5)
    SmartSensor.running = False
