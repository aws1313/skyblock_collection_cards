import requests
import os
import datetime
import operator
from flask import Flask
from flask import jsonify
from flask import send_file
from flask import current_app
from waitress import serve
import atexit
from werkzeug.middleware.proxy_fix import ProxyFix
from constants import *
import threading
import create_image
from io import BytesIO

app = Flask(APPNAME)

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

# GLOBALS
collection_infos = {}
profile_collections_old = {}
old_collection = {}
json_cache = {"sorted": [], "changed": []}
image_cache = default_img
last_req = datetime.datetime.now()
exit_event = threading.Event()


def exit_handler():
    print("wants exit")

    global exit_event
    exit_event.set()
    print("Shutting down + saving collections")
    save_to_json(os.path.join(DATA_DIR, "old_collection.json"), old_collection)
    save_to_json(os.path.join(DATA_DIR, "profile_collections_old.json"), profile_collections_old)


def get_profile_collection(api_key_, uuid_, profile_id_):
    url = f"https://api.hypixel.net/v2/skyblock/profile?key={api_key_}&profile={profile_id_}&uuid={uuid_}"
    response = requests.get(url)
    return response.json()


def prepare_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    print(f"{CACHE_DIR=}; {DATA_DIR=}")


def get_collected_items():
    url = f"https://api.hypixel.net/v2/resources/skyblock/collections"
    response = requests.get(url)
    return response.json()


def load_conf():
    conf_path = os.path.join(DATA_DIR, "config.json")
    if os.path.exists(conf_path):
        with open(conf_path) as f:
            return json.loads(f.read())
    else:
        save_to_json(conf_path, {"api-key": "", "uuid": "", "profile-id": ""})
        exit(f"Config did not exist please fill out: {conf_path}")


def prepare_collection_infos():
    collection_info_path = os.path.join(CACHE_DIR, "collection_info.json")
    if os.path.exists(collection_info_path) and (datetime.datetime.fromtimestamp(
            os.path.getmtime(collection_info_path)) > datetime.datetime.now() - datetime.timedelta(days=1)):
        return read_from_json(collection_info_path)
    else:
        url = "https://api.hypixel.net/v2/resources/skyblock/collections"
        response = requests.get(url)
        print("Got new collection_infos")
        save_to_json(collection_info_path, response.json())
        return response.json()


def add_up_members(to_add_up: dict):
    added_up = {}
    for u in to_add_up["profile"]["members"]:
        if "collection" in to_add_up["profile"]["members"][u].keys():
            for i in to_add_up["profile"]["members"][u]["collection"].keys():
                if i in added_up.keys():
                    added_up[i] += to_add_up["profile"]["members"][u]["collection"][i]
                else:
                    added_up[i] = to_add_up["profile"]["members"][u]["collection"][i]
    return added_up


def evaluate_changes(old: dict, new: dict, old_collections):
    collected = add_up_members(new)
    collected_old = add_up_members(old)
    collections = old_collections
    #print(old_collections)
    for k in collected.keys():
        if k in collections.keys():
            collections[k]["collected"] = collected[k]
        else:
            collections[k] = {"collected": collected[k]}
        if k in collected_old.keys() and (collected[k] != collected_old[k]):
            collections[k]["last_changed"] = int(datetime.datetime.now().timestamp())
            collections[k]["changed"] = True
            collections[k]["amount_changed"] = collected[k] - collected_old[k]
        else:
            collections[k]["changed"] = False
            collections[k]["amount_changed"] = 0
        if "last_changed" not in collections[k].keys():
            collections[k]["last_changed"] = 0
    #print(collections)
    return collections


def get_collections(old: dict, new: dict, old_collections):
    # Target [{"id":"COLLECTION", "display_name":"DISPLAY_NAME", "collected":1000, "tier_now":0,
    # "missing_to_next_tier":500, "percentage_to_next_tier":0.75, "last_changed":0}]
    coll = evaluate_changes(old, new, old_collections)

    items = {}
    for i in collection_infos["collections"].keys():
        for h in collection_infos["collections"][i]["items"].keys():
            items[h] = collection_infos["collections"][i]["items"][h]

    for c in coll.keys():
        if c in items.keys():
            coll[c]["display_name"] = items[c]["name"]
            coll[c]["id"] = c
            tier = 0
            # get tier now
            for tt in range(len(items[c]["tiers"])):
                t = items[c]["tiers"][tt]
                if coll[c]["collected"] > t["amountRequired"]:
                    tier = t["tier"]
                    if tier == items[c]["maxTiers"]:
                        coll[c]["maxed_out"] = True
                        coll[c]["missing_to_next_tier"] = 0
                        coll[c]["percentage_to_next_tier"] = 1
                    else:
                        # last tier amount
                        if tt > 0:
                            last_needed = items[c]["tiers"][tt]["amountRequired"]
                        else:
                            last_needed = 0
                        coll[c]["maxed_out"] = False
                        next_needed = items[c]["tiers"][tt + 1]["amountRequired"]
                        coll[c]["missing_to_next_tier"] = next_needed - coll[c]["collected"]
                        coll[c]["percentage_to_next_tier"] = (coll[c]["collected"] - last_needed) / (
                                next_needed - last_needed)


                else:
                    if tier == 0:
                        # last tier amount

                        last_needed = 0
                        coll[c]["maxed_out"] = False
                        next_needed = items[c]["tiers"][tt]["amountRequired"]
                        coll[c]["missing_to_next_tier"] = next_needed - coll[c]["collected"]
                        coll[c]["percentage_to_next_tier"] = (coll[c]["collected"] - last_needed) / (
                                next_needed - last_needed)
                    break
            coll[c]["tier_now"] = tier

    return coll


def send_pil_img(img):
    img_io = BytesIO()
    img.save(img_io, "PNG", quality=100)
    img_io.seek(0)
    return send_file(img_io, mimetype="image/png")


def start_up():
    global collection_infos
    global profile_collections_old
    global old_collection

    prepare_dirs()

    # CONFIG
    conf = load_conf()
    api_key_ = conf["api-key"]
    uuid_ = conf["uuid"]
    profile_id_ = conf["profile-id"]

    collection_infos = prepare_collection_infos()

    if os.path.exists(os.path.join(DATA_DIR, "profile_collections_old.json")):
        profile_collections_old = read_from_json(os.path.join(DATA_DIR, "profile_collections_old.json"))
    else:
        profile_collections_old = get_profile_collection(api_key_, uuid_, profile_id_)

    if os.path.exists(os.path.join(DATA_DIR, "old_collection.json")):
        old_collection = read_from_json(os.path.join(DATA_DIR, "old_collection.json"))
    else:
        old_collection = {}

    return api_key_, uuid_, profile_id_


@app.route("/")
def get_main():
    return current_app.send_static_file("index.html")


@app.route("/json")
def get_json():
    global last_req
    last_req = datetime.datetime.now()
    return jsonify(json_cache)


@app.route("/img.png")
@app.route("/ben_skyblock_collection_stream/img.png")
def get_img():
    global last_req
    last_req = datetime.datetime.now()
    return send_pil_img(image_cache)


def renew_coll(api_key, uuid, profile_id):
    global profile_collections_old
    global old_collection
    profile_collections_new = get_profile_collection(api_key, uuid, profile_id)
    save_to_json(os.path.join(CACHE_DIR, str(int(datetime.datetime.now().timestamp())) + ".json"),
                 profile_collections_new)
    c = get_collections(profile_collections_old, profile_collections_new, old_collection)
    sort = list(c.values())
    sort.sort(key=operator.itemgetter('last_changed'), reverse=True)

    # print(sort)

    # save_to_json(os.path.join(CACHE_DIR, "exp.json"),sort)

    changed = []
    for s in sort:
        if s["changed"]:
            changed.append(s)

    print(changed)

    profile_collections_old = profile_collections_new
    old_collection = c

    return {"sorted": sort, "changed": changed}


class BackgroundThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self) -> None:
        global json_cache
        global image_cache
        global exit_event
        api_key, uuid, profile_id = start_up()
        while not exit_event.is_set():
            # only request hypixel api when website is accessed
            if (datetime.datetime.now() - last_req).seconds < 10:
                json_cache = renew_coll(api_key, uuid, profile_id)
                image_cache = create_image.gen_list(json_cache["sorted"], 4)
            exit_event.wait(10)


if __name__ == '__main__':
    atexit.register(exit_handler)
    background_thread = BackgroundThread()
    background_thread.daemon = True
    background_thread.start()
    serve(app, host="0.0.0.0", port=43256)
