from db.database import db


class FileHashes(db.Model):
    name = db.Column(db.Text, primary_key=True)
    filehash = db.Column(db.String, nullable=False)
    coordinate_data = db.Column(db.Text, nullable=False)
