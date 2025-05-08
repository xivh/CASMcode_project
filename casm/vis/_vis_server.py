import os
import pathlib
import time
import webbrowser

from flask import (
    Flask,
    jsonify,
    redirect,
    send_from_directory,
)

from casm.vis import get_config

this_dir = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
dist_dir = this_dir / "dist"

app = Flask(__name__, static_folder=str(dist_dir), static_url_path="")

# from flask_cors import CORS
#
# allowed_origins = [
#     "http://localhost:3000",  # casmvis client
#     "http://localhost:3010",  # casmvis client - dev
#     "http://localhost:5000",  # casm api server
#     "http://localhost:5006",  # casm bokeh server
# ]
# CORS(
#     app,
#     resources={
#         r"/*": {"origins": allowed_origins},
#     },
# )  # The * allows for /api/data and /api/data/


@app.route("/")
def redirect_to_casm():
    return redirect("/casm/")


@app.route("/api/config/")
def config():
    return jsonify(get_config())


@app.route("/casm/")
def serve():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/casm/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)


def main():
    """Run the casm-vis server."""

    config = get_config()
    url = config["CASMVIS_SERVER"]
    port = int(url.split(":")[-1])

    import threading

    print(f"Starting casm-vis ({url})...")

    def run_app():
        app.run(host="localhost", port=port)

    # Start the Flask app in a separate thread
    thread = threading.Thread(target=run_app)
    thread.start()

    time.sleep(1.0)

    # Open the home page in the default web browser
    webbrowser.open(url)
