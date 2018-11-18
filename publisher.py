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

from ghost_client import Ghost, GhostException
from instasensor.instasensor import InstaSensor
from foosensor.foosensor import FooSensor
from openweathersensor.openweather import OpenWeather


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
                if img_path.startswith("http"):
                    response = requests.get(img_path, stream=True)
                    img = Publisher.__ghost.upload(name=img_name, data=response.raw.read())
                else:
                    img = Publisher.__ghost.upload(name=img_name, file_path=img_path)
            except (GhostException, requests.exceptions) as e:  # todo: do we need a broader catch here?
                logging.error(str(e))
        return img

    def publish(self, sensor, **kwargs):
        # find or create a sensor name
        try:
            name = sensor.__class__.__name__
            if not kwargs.get('k') or not kwargs.get('caption') or not kwargs.get('summary'):
                logging.info("Incomplete record, won't be published " + name)
                return

            # re-use or create a tag
            tags = Publisher.__ghost.tags.list(fields='name,id')
            ids = [t['id'] for t in tags if t['name'] == name]
            tag = self.__ghost.tags.get(ids[0]) if 0 < len(ids) else self.__ghost.tags.create(
                name=name,
                description=str(sensor.props['about'])[:500] if sensor.props and 'about' in sensor.props else "",
                feature_image=Publisher.__upload_img(sensor.get_featured_image()))

            # re-use summery as story, if necessary
            if not kwargs.get('story'):
                kwargs['story'] = kwargs.get('summary')

            # load and publish referenced image
            img = Publisher.__upload_img(kwargs.get('img', None))

            # look for a link to the original source
            if kwargs.get('origin'):
                kwargs['story'] = kwargs.get('story') + '\n\n[Original Source](' + str(kwargs.get('origin')) + ')'

            # now it's time to create the post
            Publisher.__ghost.posts.create(
                title=str(kwargs.get('caption')[:255]),  # up to 255 allowed
                custom_excerpt=str(kwargs.get('summary')[:300]),  # up to 300 allowed
                markdown=kwargs.get('story'),  # todo is there a size limit ?
                tags=[tag],
                feature_image=img,
                status='published',
                featured=False,
                page=False,
                locale='en_US',
                visibility='public'
            )
        except (GhostException, ConnectionError, KeyError, ValueError, TypeError) as e:
            logging.error(str(e))

    def delete_posts(self, sensor=None, all_posts=False):
        """ delete all posts that have the provided  tag"""
        try:
            posts = Publisher.__ghost.posts.list(status='all', include='tags')
            ids = []
            for _ in range(posts.pages):
                last, posts = posts, posts.next_page()
                ids.extend([p['id'] for p in last if
                            all_posts or (p['tags'] and p['tags'][0]['name'] == sensor.__class__.__name__)])
                if not posts:
                    break
            for i in ids:
                Publisher.__ghost.posts.delete(i)
                logging.info("deleted")

        except GhostException as e:
            logging.error(str(e))

    def delete(self, tag):
        """ delete all posts that have the provided  tag"""
        try:
            posts = Publisher.__ghost.posts.list(status='all', include='tags')
            ids = []
            for _ in range(posts.pages):
                last, posts = posts, posts.next_page()
                for p in last:
                    for sensor, upd in tag:
                        if p['tags'] and p['tags'][0]['name'] == sensor.__class__.__name__ \
                                and p['title'] == upd['caption'] \
                                and p['custom_excerpt'] == upd['summary']:
                            ids.append(p.id)
                if not posts:
                    break
            # for i in ids:
            #     Publisher.__ghost.posts.delete(i)
        except GhostException as e:
            logging.error(str(e))

    def purge(self, sensor=None, all_sensors=False):
        """ delete all posts and the tag associated with the given sensor """
        self.delete_posts(sensor, all_sensors)
        tags = Publisher.__ghost.tags.list(fields='name,id')
        ids = [t['id'] for t in tags if all_sensors or t['name'] == sensor.__class__.__name__]
        if 0 < len(ids):
            self.__ghost.tags.delete(ids[0])
            logging.info("purged")

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


if __name__ == "__main__":

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        filename=os.path.join(os.getcwd(), 'logs', 'publisher.log'),
        filemode='a',
        format='%(asctime)s - %(module)s - %(lineno)d - %(levelname)s - %(message)s')

    publisher = Publisher()
    publisher.purge(FooSensor())

    s = OpenWeather()
    publisher.purge(s)

    content = s.get_all()
    for c in content:
        publisher.publish(s, **c)

    s = InstaSensor()
    publisher.purge(s)

    content = s.get_all()
    for c in content:
        publisher.publish(s, **c)
