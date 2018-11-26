"""
    Maintaining content for the GHost web-blog site GCCCD Journal
"""
__version__ = "1.0"
__author__ = "Wolf Paulus"
__email__ = "wolf.paulus@gcccd.edu"

import logging
import os
from publisher.publisher import Publisher

if __name__ == "__main__":
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        filename=os.path.join(os.getcwd(), 'logs', 'publisher.log'),
        filemode='w',
        format='%(asctime)s - %(module)s - %(lineno)d - %(levelname)s - %(message)s')

    # from Stocks.PhilSensor import PhilSensor
    # s = PhilSensor()
    # k = 0
    # for d in s.get_all():
    #     for key in d.keys():
    #         print("{} : {}".format(key, d.get(key)))
    #         k = d.get('k')
    # print(s.has_updates(k))

    publisher = Publisher()
    publisher.purge(all_sensors=True)

    result = publisher.get_all()  # list of tuples i.e. (sensors name, list of dictionaries)
    result.sort(key=lambda x: len(x[1]), reverse=True)  # sensor with least number of posts comes 1st

    balanced_list = []
    pos, step = 0, 1
    for tup in result:
        for p in tup[1]:  # list of dictionaries newest 1st
            balanced_list.insert(pos, (tup[0], p))
            pos += step
        pos, step = step, step + 1

    for tup in balanced_list[::-1]:
        publisher.publish(tup[0], **tup[1])
