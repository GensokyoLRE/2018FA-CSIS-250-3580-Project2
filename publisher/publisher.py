"""
A consumer for GCCCD Software Sensors, takes content from sensors and publishes into Ghost
"""

__version__ = "2.0"
__author__ = "Wolf Paulus"
__email__ = "wolf.paulus@gcccd.edu"

import logging
import os
import importlib
import time
import copy
import requests
from sensor import SensorX
from ghost_client import Ghost, GhostException


class Publisher(SensorX):
    """ requires external lib to access Ghost server: ghost-client (v0.0.4)  """

    def __init__(self):
        super().__init__(os.path.join(os.path.dirname(__file__), self.__class__.__name__))
        try:
            self.__ghost = Ghost(self.props['server'],
                                 client_id=self.props['client_id'],
                                 client_secret=self.props['client_secret'])
            self.__ghost.login(self.props['user'], self.props['password'])
        except GhostException as e:
            logging.error(str(e))

    def has_updates(self, k=None):
        """
        :param k: not unsed, only here for interface compliance
        :return: total number of new 'records' sensors could provide, since the last get_content() or get_all() calls
        """
        if self._request_allowed():
            # remember current state of ks:
            backup = copy.deepcopy(self.props["sensors"])
            new_content = self._fetch_data()
            self.props["sensors"] = backup
            self._save_settings()
            return sum(len(tup[1]) for tup in new_content)
        return 0

    def get_content(self, k=None):
        """
        get only the new data (since the last get_all() or get_content()), from all registered sensors
        :param k: not unsed, only here for interface compliance
        :return: list of tuple, for each sensor (sensor_name, list of dictionaries, (each of which represents a post))

        """
        return self._fetch_data() if self._request_allowed() else []

    def get_all(self):
        """
        get the data from all registered sensors
        :return: list of tuple, for each sensor (sensor_name, list of dictionaries, (each of which represents a post))
        """
        return self._fetch_data(True) if self._request_allowed() else []

    def _fetch_data(self, everything=False):
        """
        get the data from all registered sensors
        updating ks and access time in properties file along the way.
        :param everything: if True get_all is called on each sensor, else get_content
        :return: tuple for each sensor (sensor, list of dictionaries, (each of which represents a post))
        """
        all_data = []
        try:
            sensors = self.props["sensors"]
            self.props['last_used'] = int(time.time())
            for key in sensors.keys():
                sensor = getattr(importlib.import_module(sensors[key]['module']), key)()
                data = sensor.get_all() if everything else sensor.get_content(sensors[key].get('k', ''))
                if data and 0 < len(data):
                    # remember k
                    self.props['sensors'][sensor.__class__.__name__]['k'] = data[-1]['k']
                    all_data.append((sensor, data))
            self._save_settings()
        except (ConnectionError, KeyError, ValueError, TypeError) as e:
            logging.error(e)
        return all_data

    def __upload_img(self, img_path):
        """
        Updload an image from a url and filepath into the CMS
        :param img_path: url starting with http, or a file path to a local file
        :return: image file path onside the CMS
        """
        img = ''
        if img_path is not None:
            try:
                img_name = os.path.basename(img_path)
                if img_path.startswith("http"):
                    response = requests.get(img_path, stream=True)
                    img = self.__ghost.upload(name=img_name, data=response.raw.read())
                else:
                    img = self.__ghost.upload(name=img_name, file_path=img_path)
            except (GhostException, requests.exceptions) as e:
                logging.error(str(e))
        return img

    def publish(self, sensor, **kwargs):
        """
        Publish the provided info as a not post, tagged with the sensor's name.
        If an image is provided in kwargs, if will be copied into the CMS
        If the tag does not exist, it will be created, with image and all that.
        Old duplicate posts will be deleted, before being re-published.
        :param sensor: class name of a sensor
        :param kwargs: at least k, caption, and summary, nice to have img, origin, story
        """
        try:
            name = sensor.__class__.__name__
            if not kwargs.get('k') or not kwargs.get('caption') or not kwargs.get('summary'):
                logging.info(name + " incomplete records, won't be published.")
                return
            ids = self.__find_dup(name, kwargs.get('caption'), kwargs.get('summary'))
            if 0 < len(ids):
                logging.info(name + " : duplicate records, won't be published " + kwargs.get('caption'))
                # alternatively, the duplicates could be deleted as well, like this:
                # for i in ids: self.__ghost.posts.delete(i)
                return

            # re-use or create a tag
            tags = self.__ghost.tags.list(fields='name,id')
            ids = [t['id'] for t in tags if t['name'] == name]
            tag = self.__ghost.tags.get(ids[0]) if 0 < len(ids) else self.__ghost.tags.create(
                name=name,
                description=str(sensor.props['about'])[:500] if sensor.props and 'about' in sensor.props else "",
                feature_image=self.__upload_img(sensor.get_featured_image()))

            # re-use summery as story, if necessary
            if not kwargs.get('story'):
                kwargs['story'] = kwargs.get('summary')

            # load and publish referenced image
            img = self.__upload_img(kwargs.get('img', None))

            # look for a link to the original source
            if kwargs.get('origin'):
                kwargs['story'] = kwargs.get('story') + '\n\n[Original Source](' + str(kwargs.get('origin')) + ')'
            # hack only needed for the bleak theme
            # if img:
            #     kwargs['story'] = "![Logo]({})\n".format(img) + kwargs.get('story')
            # now it's time to create the post
            self.__ghost.posts.create(
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

    def __delete_posts(self, sensor=None, all_posts=False):
        """
        delete all posts that have the provided tag, or all_posts
        :param sensor:
        :param all_posts: call with True, to delete all posts in the CMS
        """
        try:
            posts = self.__ghost.posts.list(status='all', include='tags')
            ids = []
            for _ in range(posts.pages):
                last, posts = posts, posts.next_page()
                ids.extend([p['id'] for p in last if
                            all_posts or (p['tags'] and p['tags'][0]['name'] == sensor.__class__.__name__)])
                if not posts:
                    break
            for i in ids:
                self.__ghost.posts.delete(i)
                logging.info("deleted")
        except GhostException as e:
            logging.error(str(e))

    def __find_dup(self, sensor_name, caption, summary):
        """
        find already published duplicate posts
        :param sensor_name: class name of the sensor
        :param caption: caption of the post
        :param summary: summary of the post
        :return: list of ids of duplicates
        """
        ids = []
        try:
            posts = self.__ghost.posts.list(status='all', include='tags')
            for _ in range(posts.pages):
                last, posts = posts, posts.next_page()
                ids.extend([p['id'] for p in last if p['tags'] and p['tags'][0]['name'] == sensor_name
                            and p['title'] == caption[:255]
                            and p['custom_excerpt'] == summary[:300]])
                if not posts:
                    break
        except GhostException as e:
            logging.error(str(e))
        return ids

    def purge(self, sensor=None, all_sensors=False):
        """
        delete all posts and the tag associated with the given sensor
        :param sensor: class name of the sensor
        :param all_sensors: call with True, to delete all posts and tags in the CMS
        :return:
        """
        self.__delete_posts(sensor, all_sensors)
        tags = self.__ghost.tags.list(fields='name,id')
        ids = [t['id'] for t in tags if all_sensors or t['name'] == sensor.__class__.__name__]
        if 0 < len(ids):
            self.__ghost.tags.delete(ids[0])
            logging.info("purged")

    def _k_wipe(self):
        """ removing k values from properties, only for testing purposes. """
        sensors = self.props["sensors"]
        for key in sensors.keys():
            del (sensors[key]['k'])


if __name__ == "__main__":
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        filename=os.path.join(os.getcwd(), 'logs', 'publisher.log'),
        filemode='w',
        format='%(asctime)s - %(module)s - %(lineno)d - %(levelname)s - %(message)s')

    publisher = Publisher()

    ps = publisher.get_all()
    for post in ps:
        print(post[0], len(post[1]))
    print(publisher.has_updates())
    time.sleep(11)
    print(publisher.has_updates())
    publisher._k_wipe()
    print(publisher.has_updates())
