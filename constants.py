import json
from PIL import Image
from platformdirs import user_cache_dir, user_data_dir

DEBUG = True

APPNAME = "ben_skyblock_collection_stream"
AUTHOR = "io.github.aws1313"


CACHE_DIR = user_cache_dir(appname=APPNAME, appauthor=AUTHOR) if DEBUG else "/data/cache"

DATA_DIR = user_data_dir(appname=APPNAME, appauthor=AUTHOR) if DEBUG else "/data/data"
default_img = Image.new("RGBA", (750,150))


def save_to_json(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)


def read_from_json(filename):
    with open(filename) as f:
        return json.loads(f.read())
