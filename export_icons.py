# export collections from https://hypixel-skyblock.fandom.com/wiki/Collections
import difflib
import itertools
import json
import os.path

import requests
from bs4 import BeautifulSoup

from constants import CACHE_DIR

with open("collections_and_levels.html") as f:
    soup = BeautifulSoup(f.read(), "html.parser")


def grouper(n, iterable, fillvalue=None):
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


l = soup.find_all("table", class_="wikitable")
grouped = list(grouper(2, l))
coll = {}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36 SE 2.X MetaSr 1.0"}

coll_file = os.path.join(CACHE_DIR, "collection_info.json")
allowed_names = []
if os.path.exists(coll_file):
    with open(coll_file) as f:
        collections = json.load(f)
    for c in collections["collections"].values():
        for i in c["items"].values():
            allowed_names.append(i["name"].replace(" ", "_"))

for i in grouped:
    name = i[0].find("tr")["id"]
    print(name)
    img_src = i[0].find("tr").find("img")["src"]
    img_src = img_src[:img_src.find(".png")+4]

    print(img_src)



    try:
        response = requests.get(img_src, headers=headers)

        if not allowed_names or name in allowed_names:
            dp_name = name

        else:
            poss_choice = difflib.get_close_matches(name, allowed_names, n=5)

            print("Name could not be found, please choose one of the following: {}".format(poss_choice))
            dp_name = input(f"Name {name} (how the icon should be named excluding .png): ")


        with open('assets/icons/'+dp_name+".png", "wb") as file:
            file.write(response.content)
    except Exception as e:
        print("failed"+name+" " + img_src)
        print(e)
    levels = {}



    coll[name] = levels
print(coll)
print(len(coll))
