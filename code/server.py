import os
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    current_user,
    logout_user,
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import plotly.graph_objects as go
import plotly
import tempfile
from geo_admin_tools import *
from db.database import db
from db.db_utils import JSON_FILE_LOCATION
from db.models import User, File
from utils import getCurrentTimeString

app = Flask(__name__)

app.config["SECRET_KEY"] = "PnC3Xr?nxgjsXN$o"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)
login_manager.login_message = "Du musst angemeldet sein, um diese Seite zu sehen!"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


KML_FILE_LOCATION = "./files/kml/"
XLSX_FILE_LOCATION = "./files/xlsx/"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register_post():
    email = request.form.get("email")
    name = request.form.get("name")
    password = request.form.get("password")

    user = User.query.filter_by(email=email).first()
    if user:
        flash("Email-Addresse ist bereits vergeben!")
        return redirect(url_for("register"))

    new_user = User(
        email=email,
        name=name,
        password=generate_password_hash(password, method="sha256"),
    )
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for("login"))


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_post():
    email = request.form.get("email")
    password = request.form.get("password")
    remember = True if request.form.get("remember") else False

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        flash("Irgendewas stimmt nicht. Überprüfe bitte deine Angaben.")
        return redirect(url_for("login"))

    login_user(user, remember=remember)
    return redirect(url_for("home"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/home")
@login_required
def home():
    files = current_user.files
    return render_template("home.html", files=files, user=current_user)


@app.route("/upload", methods=["POST"])
@login_required
def upload_kml():
    if "file" not in request.files:
        return "No file uploaded"
    file = request.files["file"]
    if file.filename == "":
        return "No file uploaded"

    current_files = os.listdir(KML_FILE_LOCATION)
    fname = getCurrentTimeString()
    while f"{fname}.json" in current_files:
        fname = str(int(fname) + 1)
    if file:
        new_file = File(
            title=file.filename.split(".")[0],
            fname=fname,
        )
        current_user.files.append(new_file)
        db.session.commit()
        combineAndSave(file, fname)

        return redirect(url_for("home"))


@app.route("/edit_kml/<file_id>")
@login_required
def edit_kml(file_id):
    file = File.query.get(file_id)
    if file.uploaded_by_userid != current_user.id:
        flash("Du hast keine Berechtigungen auf diese Datei!")
        return redirect(url_for("home"))
    data = getCoordinateData(file.fname)
    plots = createPlots(data["poi"], data["coords"])

    return render_template(
        "edit_kml.html",
        plots=plots,
        file=file,
        poi=data["poi"],
        center=getCenterCoords(data["coords"]),
        user=current_user,
    )


@app.route("/delete_kml/<file_id>")
@login_required
def delete_kml(file_id):
    removeRecord(file_id)
    return redirect(url_for("home"))


@app.route("/download_kml/<file_id>/<line_name>")
def download_kml(file_id, line_name):
    file = File.query.get(file_id)
    fname = file.fname
    tmp = tempfile.TemporaryFile()
    content = generate_kml(fname, line_name)
    tmp.write(content)
    tmp.seek(0)
    return send_file(
        tmp, as_attachment=True, download_name=f"{file.title}_{line_name}.kml"
    )


@app.route("/download_xlsx/<file_id>/<line_name>")
def download_xlsx(file_id, line_name):
    file = File.query.get(file_id)
    fname = file.fname
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx")
    book = generate_xlsx(fname, line_name)
    book.save(tmp)
    tmp.seek(0)
    return send_file(
        tmp, as_attachment=True, download_name=f"{file.title}_{line_name}.xlsx"
    )


@app.route("/break_kml", methods=["POST"])
@login_required
def break_kml():
    file_id = request.form["file_id"]
    break_point = request.form["breaker"]
    line_segment = request.form["linesegment"]

    fname = File.query.get(file_id).fname
    breakLineAtPoint(fname, line_segment, break_point)
    return redirect(url_for("edit_kml", file_id=file_id))


@app.route("/update_poi", methods={"POST"})
@login_required
def update_poi():
    form = request.form
    file_id = form["file_id"]
    updatePoiNames(form)
    updatePoiDisplay(form)

    return redirect(url_for("edit_kml", file_id=file_id))


def createPlots(poi, coords):
    out = {}
    for key, item in coords.items():
        out[key] = []
        for template in ["plotly", "plotly_dark"]:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=[p["dist"] for p in poi[key]],
                    y=[p["alt"] for p in poi[key]],
                    hovertemplate="Distanz: %{x} m, Höhe: %{y} m",
                    name="MZB",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[p["dist"] for p in item],
                    y=[p["alt"] for p in item],
                    hovertemplate="Distanz: %{x} m, Höhe: %{y} m",
                    name="Profil",
                )
            )

            fig.update_layout(
                xaxis_title="Distanz (m)",
                yaxis_title="Höhe (m)",
                title_text="",
                template=template,
                width=400,
                height=300,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )

            out[key].append(
                plotly.offline.plot(fig, include_plotlyjs=False, output_type="div")
            )

    return out


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
