from db.database import db
from db.models import FileHashes
import json
import os

JSON_FILE_LOCATION = "db/json/"


def saveCoordinateData(name, coordinate_data):
    with open(JSON_FILE_LOCATION + name + ".json", "w") as f:
        json.dump(coordinate_data, f)


def getCoordinateData(name):
    with open(JSON_FILE_LOCATION + name + ".json", "r") as f:
        return json.load(f)


def deleteCoordinateData(name):
    os.remove(JSON_FILE_LOCATION + name + ".json")
