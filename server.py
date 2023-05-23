from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["GET", "POST"])
def upload_kml():
    if request.method == "GET":
        return "Wrong request Type"
    print(request.files["file"])
    if "file" not in request.files:
        return "No file uploaded"
    file = request.files["file"]
    if file.filename == "":
        return "No file uploaded"
    print("here")
    if file and allowed_file(file.filename):
        print(file.read())
        filename = secure_filename(file.filename)
        return redirect(url_for("index"))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "kml"


if __name__ == "__main__":
    app.run(debug=True)
