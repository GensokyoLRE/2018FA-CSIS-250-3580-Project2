
import requests
from urllib.parse import quote
import pprint
import json

API_KEY = 'pacc4ghRE-bYl6Y6S45N9RHn2ElT5DyCJMbesOU8mYiVuMNx1tReWqsg6CcD5yK3tY8etGwvRwYipANjPStUDr_Rk_jZT2BAqc2Wkelf2Xu79IXR-TWjR4luBczgW3Yx'
API_HOST = 'https://api.yelp.com'
SEARCH_URL = '/v3/businesses/search'
BUSINESS_URL = '/v3/businesses/'
MAX = 50
URL = 'https://api.yelp.com/v3/businesses/search'
term = 'restaurant'
location = 'El Cajon'
parameters = {'term': term, 'location': location, 'limit': MAX}
headers = {'Authorization': 'Bearer ' + API_KEY}
response = requests.request('GET', URL, headers=headers, params=parameters)
response_json = response.json()
businesses = response_json.get('businesses')

print(len(businesses))
pprint.pprint(businesses)

with open('results_raw.json', 'w') as f:
    json.dump(businesses, f, indent=2)
