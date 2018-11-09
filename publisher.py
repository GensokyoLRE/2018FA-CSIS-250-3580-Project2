"""
A consumer for GCCCD Software Sensors, takes content from sensors and publishes into Ghost
"""
from foosensor.foosensor import FooSensor

__version__ = "2.0"
__author__ = "Wolf Paulus"
__email__ = "wolf.paulus@gcccd.edu"

import os
import json
import requests
from ghost_client import Ghost, GhostException
from instasensor.instasensor import InstaSensor


# noinspection PyMethodMayBeStatic
class Publisher:
    """ requires external lib to access Ghost server: ghost-client (v0.0.4)  """
    __ghost = None

    def __init__(self):
        if Publisher.__ghost is None:
            Publisher.__ghost = Publisher.__connect()

    @staticmethod
    def __upload_img(img_path):
        img = ''
        if img_path is not None:
            try:
                img_name = os.path.basename(img_path)
                response = requests.get(img_path, stream=True)
                img = Publisher.__ghost.upload(name=img_name, data=response.raw.read())
            except requests.exceptions:
                print(requests.exceptions)
        return img

    def publish(self, sensor, **kwargs):
        # find or create a sensor name
        name = sensor.__class__.__name__
        # re-use or create a tag
        tags = Publisher.__ghost.tags.list(fields='name,id')
        ids = [t['id'] for t in tags if t['name'] == name]
        tag = Publisher.__ghost.tags.get(ids[0]) if 0 < len(ids) else Publisher.__ghost.tags.create(name=name)
        # load and publish referenced image
        img = Publisher.__upload_img(kwargs.get('img', None))
        # look for a link to the original source
        if kwargs.get('origin'):
            if kwargs.get('story'):
                kwargs['story'] = kwargs.get('story') + '\nOriginal Source](' + str(kwargs.get('origin')) + ')'
            else:
                kwargs['story'] = '\n[Original Source](' + str(kwargs.get('origin')) + ')'
        # create a post
        Publisher.__ghost.posts.create(
            title=str(kwargs.get('caption'))[0:80],  # up to 255 allowed
            markdown=kwargs.get('story'),
            custom_excerpt=str(kwargs.get('summary'))[:200],
            tags=[tag],
            feature_image=img,
            status='published',
            featured=False,
            page=False,
            locale='en_US',
            visibility='public'
            # slug='my custom-slug',
        )

    def delete_posts(self, sensor):
        """ delete all posts that have the provided  tag"""
        tag = sensor.__class__.__name__
        posts = Publisher.__ghost.posts.list(status='all', include='tags')
        ids = []
        for _ in range(posts.pages):
            last, posts = posts, posts.next_page()
            for p in last:
                if p['tags'][0]['name'] == tag:  # this might need some work, if more than one tag is used
                    ids.append(p.id)
            if not posts:
                break
        for i in ids:
            Publisher.__ghost.posts.delete(i)

    @staticmethod
    def __connect():
        """ ghost allows 'only;' 100 logins per hour from a single IP Address ..."""
        try:
            with open(os.path.join(os.path.dirname(__file__), 'publisher.json')) as json_text:
                settings = json.load(json_text)
            ghost = Ghost(settings['server'], client_id=settings['client_id'], client_secret=settings['client_secret'])
            ghost.login(settings['user'], settings['password'])
            return ghost
        except GhostException:
            print()
            return None


if __name__ == "__main__":
    # GHOST 'Only 100 request per IP address per hour!!
    # ghost_client import Ghost -->  https://github.com/rycus86/ghost-client
    # look for client_id and client_id in the html code here: http://localhost:2368

    my_sensor = FooSensor()
    for record in my_sensor.get_all():
        Publisher().publish(my_sensor, **record)
        print(record)

    my_sensor = InstaSensor()
    Publisher().delete_posts(my_sensor)

    stories = my_sensor.get_all()
    for s in stories:
        Publisher().publish(my_sensor, **s)
    print(" Stories posted : ", str(len(stories)))
