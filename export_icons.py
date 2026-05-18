# export collections from https://hypixel-skyblock.fandom.com/wiki/Collections
import itertools
import json
import urllib.request

import requests
import roman
from bs4 import BeautifulSoup

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

for i in grouped:
    name = i[0].find("tr")["id"]
    print(name)
    img_src = i[0].find("tr").find("img")["src"]
    img_src = img_src[:img_src.find(".png")+4]

    print(img_src)



    try:
        response = requests.get(img_src, headers=headers)
        with open('assets/icons/'+name+".png", "wb") as file:
            file.write(response.content)
    except Exception as e:
        print("failed"+name+" " + img_src)
        print(e)
    levels = {}



    coll[name] = levels
print(coll)
print(len(coll))
