import json
import pprint


with open('results_raw.json') as f:
    data = json.load(f)
len_data = len(data)
for x in range(len(data)-1, -1, -1):
    try:
        if data[x]['is_closed'] is True or \
                len(data[x]['price']) > 1 or \
                'delivery' not in data[x]['transactions']:
            data.pop(x)
    except:
        data.pop(x)

bus_final = []
for item in data:
    filtered_dict = {k: v for (k, v) in item.items() if 'name' in k or 'categories' in k
                     or 'location' in k or 'display_phone' in k or 'url' in k or 'image_url' in k
                     or 'transactions' in k}

    address = filtered_dict['location']['display_address']
    filtered_dict['location'] = ", ".join(address)
    transactions = filtered_dict['transactions']
    filtered_dict['transactions'] = ", ".join(transactions)
    description = [list(d.values()) for d in filtered_dict['categories']]
    for x in range(len(description)):
        description[0].extend(description[x])
    description_str = (" ".join(description[0])).lower()
    filtered_dict['categories'] = ", ".join(list(set(description_str.split(" "))))
    bus_final.append(filtered_dict)

print("Of the top", len_data, "results for your search,", len(bus_final),
      "are open, inexpensive, and offer delivery service:\n")
print(len(bus_final))
pprint.pprint(bus_final)


with open('results_final.json', 'w') as f:
    json.dump(bus_final, f, indent=2, sort_keys=True)

