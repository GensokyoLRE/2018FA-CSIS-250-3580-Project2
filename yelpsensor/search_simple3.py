import requests
import json
import pprint

with open('yelp.json') as json_text:
    yelp_json = json.load(json_text)
response = requests.request('GET', yelp_json['URL'], headers=yelp_json['headers'], params=yelp_json['parameters'])
businesses = response.json().get('businesses')

len_businesses = len(businesses)
for x in range(len_businesses-1, -1, -1):
    try:
        if businesses[x]['is_closed'] is True or len(businesses[x]['price']) > 1\
                or 'delivery' not in businesses[x]['transactions']:
            businesses.pop(x)
    except:
        businesses.pop(x)
final_dict = []
for item in businesses:
    filtered_dict = {k: v for (k, v) in item.items() if 'name' in k or 'categories' in k
                     or 'location' in k or 'display_phone' in k or 'url' in k or 'image_url' in k}
    address = filtered_dict['location']['display_address']
    filtered_dict['location'] = " ".join(address)
    description = filtered_dict['categories'][0]['alias']
    filtered_dict['categories'] = description
    final_dict.append(filtered_dict)

print("Of the top", len_businesses, "results for your search,", len(final_dict),
      "are open, inexpensive, and offer delivery service:\n")
pprint.pprint(final_dict)
with open('results_final.json', 'w') as f:
    json.dump(final_dict, f, indent=2, sort_keys=True)
