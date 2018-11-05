# coding: utf-8
import requests
import geopy.distance
import tqdm
import sys

listing_content = requests.get("https://worldmarket.shoplocal.com/WorldMarket/sitemap/locations/").content
locations = { }
all_stores= [ line[:-7].strip() for line in listing_content.splitlines() if line.endswith(b"<br />") and line.count(b",") >= 2 ]
street_addrs = set(s.split(b",")[0] for s in all_stores)
cities = set(s.split(b",")[1].strip() for s in all_stores)
for _addr in tqdm.tqdm(all_stores):
    if _addr in locations:
        continue
    print("Looking up:", _addr)
    response = requests.get("https://nominatim.openstreetmap.org/search?q=%s&format=json" % _addr.decode('utf-8')).json()
    if not response:
        print("... trying just city.")
        response = requests.get("https://nominatim.openstreetmap.org/search?q=%s&format=json" % _addr.split(b",", 1)[1].decode('utf-8')).json()
    if not response:
        print("... no response.")
    locations[_addr] = ( float(response[0]["lat"]), float(response[0]["lon"]) )
    print("... got:", locations[_addr])


def find_item(item_code):
    availability = [ ]
    checked = set()
    for addr,coords in tqdm.tqdm(locations.items()):
        print("Checking",addr)
        if any(geopy.distance.distance(coords, a).miles < 40 for a in checked):
            print("... already checked within 40 miles of",addr)
            continue
        r = requests.post("https://www.worldmarket.com/addToBasket.do?method=findStores", data={"latitude": coords[0], "longitude": coords[1], "option": "none", "optionTypes": 0, "productPk": item_code, "qty": 1, "selectedRadius": 50}, allow_redirects=False)
        if r.status_code != 200:
            print("... ERROR: something went wrong with:", addr, r.request.body)
            continue
        checked.add(coords)
        c = r.content
        if b"Available" in r.content:
            relevant_lines = [ s for s in c.splitlines() if b"Available" in s or (b">" in s and s.split(b">")[-1].strip(b",") in cities) ]
            for n,s in enumerate(relevant_lines):
                if b"Available" in s:
                    where = relevant_lines[n-1].strip(b"\t").replace(b"<br />", b", ") + b", " + addr.split(b", ")[-1]
                    print("... AVAILABLE:", where)
                    availability.append(where)
    return availability

if __name__ == "__main__":
    for item in sys.argv[1]:
        print("%d AVAILABLE AT:", int(item))
        print(b"\n".join(find_item(int(item))).decode('utf-8'))
