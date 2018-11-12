import requests
import json

response = requests.get(
    "https://api.openweathermap.org/data/2.5/forecast?q=El Cajon,us&appid=f2a8e1eb9507255e2cae81800bdb7097")
for entry in json.loads(response.text)['list']:
    print(entry['weather'][0]['description'], entry['wind']['speed'])
