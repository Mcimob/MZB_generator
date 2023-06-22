from db.database import db
from flask_login import UserMixin
import datetime


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    admin = db.Column(db.Boolean(), default=False)


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    fname = db.Column(db.String(100), unique=True)
    date_uploaded = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    uploaded_by_userid = db.Column(db.Integer, db.ForeignKey("user.id"))
    uploaded_by = db.relationship("User", backref=db.backref("files", lazy=True))


class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    text = db.Column(db.String(10_000))
    suggestion_type = db.Column(db.String(20))
    date_added = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    uploaded_by_userid = db.Column(db.Integer, db.ForeignKey("user.id"))
    uploaded_by = db.relationship("User", backref=db.backref("suggestions", lazy=True))
