from db.database import db
from db.models import FileHashes
import json


def saveFileHashData(name, fileHash, coordinate_data):
    getFileHashData(name)
    newRow = FileHashes(
        name=name, filehash=fileHash, coordinate_data=json.dumps(coordinate_data)
    )
    db.session.add(newRow)
    db.session.commit()
    return


def getFileHashData(name):
    row = FileHashes.query.filter_by(name=name).first()
    print(row)
    return row
