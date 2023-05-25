import os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_file,
)
from werkzeug.utils import secure_filename
import plotly.graph_objects as go
import plotly
from geo_admin_tools import *
from db.database import db
from db.db_utils import getFileHashData

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///geo_admin_tools.db"
db.init_app(app)
with app.app_context():
    db.create_all()
    getFileHashData("map")
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
        combineAndSave(file, KML_FILE_LOCATION + filename)
        # file.save(KML_FILE_LOCATION + filename)
        # return redirect(url_for("index"))
        return "Success!"


@app.route("/edit_kml/<filename>")
def edit_kml(filename):
    if filename.split(".")[0] + ".xlsx" not in os.listdir(XLSX_FILE_LOCATION):
        return redirect(url_for("generate_xlsx", filename=filename))
    poi, coords = generatePoiAndCoords(filename)
    plot = createPlot(poi, coords)
    return render_template("edit_kml.html", plot=plot, filename=filename, poi=poi)


@app.route("/generate_xlsx/<filename>")
def generate_xlsx(filename):
    generate(filename)
    return redirect(url_for("edit_kml", filename=filename))


@app.route("/download/<filename>")
def download(filename):
    file_type = filename.split(".")[1]
    return send_file(f"./files/{file_type}/{filename}", as_attachment=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "kml"


def createPlot(poi, coords):
    fig1 = go.Scatter(x=[p["dist"] for p in poi], y=[p["alt"] for p in poi])
    fig2 = go.Scatter(x=[p["dist"] for p in coords], y=[p["alt"] for p in coords])
    return plotly.offline.plot([fig1, fig2], include_plotlyjs=False, output_type="div")


if __name__ == "__main__":
    app.run(debug=True)
