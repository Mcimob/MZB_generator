from db.database import db


class FileHashes(db.Model):
    name = db.Column(db.Text, primary_key=True)
    coordinate_data = db.Column(db.Text, nullable=False)
