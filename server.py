from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import os
from geo_admin_tools import *

app = Flask(__name__)
KML_FILE_LOCATION = "./files/kml/"
XLSX_FILE_LOCATION = "./files/xlsx/"


@app.route("/")
def index():
    files = os.listdir(KML_FILE_LOCATION)
    return render_template("index.html", files=files)


@app.route("/upload", methods=["POST"])
def upload_kml():
    if "file" not in request.files:
        return "No file uploaded"
    file = request.files["file"]
    if file.filename == "":
        return "No file uploaded"
    current_files = os.listdir(KML_FILE_LOCATION)
    if file.filename in current_files:
        return "Please choose a different filename"
    print("here")
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(KML_FILE_LOCATION + filename)
        return redirect(url_for("index"))


@app.route("/edit_kml/<filename>")
def edit_kml(filename):
    if filename.split(".")[0] + ".xlsx" not in os.listdir(XLSX_FILE_LOCATION):
        return redirect(url_for("generate_xlsx", filename=filename))
    return render_template("edit_kml.html")


@app.route("/generate_xlsx/<filename>")
def generate_xlsx(filename):
    generate(filename)
    return redirect(url_for("edit_kml", filename=filename))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "kml"


if __name__ == "__main__":
    app.run(debug=True)
