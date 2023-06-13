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
from db.db_utils import JSON_FILE_LOCATION
import tempfile

app = Flask(__name__)

KML_FILE_LOCATION = "./files/kml/"
XLSX_FILE_LOCATION = "./files/xlsx/"


@app.route("/")
def index():
    files = os.listdir(JSON_FILE_LOCATION)
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
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        combineAndSave(file, KML_FILE_LOCATION + filename)

        return redirect(url_for("index"))


@app.route("/edit_kml/<filename>")
def edit_kml(filename):
    data = getCoordinateData(filename)
    plots = createPlots(data["poi"], data["coords"])

    return render_template(
        "edit_kml.html",
        plots=plots,
        filename=filename,
        poi=data["poi"],
        suppliedMarkers=data["markers"],
    )


@app.route("/delete_kml/<filename>")
def delete_kml(filename):
    removeRecord(filename)
    return redirect(url_for("index"))


@app.route("/download/<filename>")
def download(filename):
    file_type = filename.split(".")[1]
    return send_file(f"./files/{file_type}/{filename}", as_attachment=True)


@app.route("/download_kml/<fname>/<line_name>")
def download_kml(fname, line_name):
    tmp = tempfile.TemporaryFile()
    content = generate_kml(fname, line_name)
    tmp.write(content)
    tmp.seek(0)
    return send_file(tmp, as_attachment=True, download_name=f"{fname}_{line_name}.kml")


@app.route("/break_kml", methods=["POST"])
def break_kml():
    fname = request.form["filename"]
    break_point = request.form["breaker"]
    line_segment = request.form["linesegment"]
    breakLineAtPoint(fname, line_segment, break_point)
    return redirect(url_for("edit_kml", filename=fname))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "kml"


def createPlots(poi, coords):
    out = {}
    for key, item in coords.items():
        fig1 = go.Scatter(
            x=[p["dist"] for p in poi[key]], y=[p["alt"] for p in poi[key]]
        )
        fig2 = go.Scatter(x=[p["dist"] for p in item], y=[p["alt"] for p in item])
        out[key] = plotly.offline.plot(
            [fig1, fig2], include_plotlyjs=False, output_type="div"
        )

    return out


if __name__ == "__main__":
    app.run(debug=True)
