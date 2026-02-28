import os
import pathlib
import time
import webbrowser

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send

from casm.vis import get_config

this_dir = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
dist_dir = this_dir / "dist"


class _SafeStaticFiles(StaticFiles):
    """StaticFiles subclass that gracefully rejects WebSocket connections."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1000})
            return
        await super().__call__(scope, receive, send)


app = FastAPI()


@app.get("/")
def redirect_to_casm():
    return RedirectResponse(url="/casm/")


@app.get("/api/config/")
def config():
    return get_config()


app.mount("/casm", _SafeStaticFiles(directory=str(dist_dir), html=True), name="static")
app.mount("/", _SafeStaticFiles(directory=str(dist_dir)), name="root_static")


def main():
    """Run the casm-vis server."""

    import threading

    import uvicorn

    config_data = get_config()
    url = config_data["CASMVIS_SERVER"]
    port = int(url.split(":")[-1])

    print(f"Starting casm-vis ({url})...")

    def run_app():
        uvicorn.run(app, host="localhost", port=port)

    # Start the app in a separate thread
    thread = threading.Thread(target=run_app)
    thread.start()

    time.sleep(1.0)

    # Open the home page in the default web browser
    webbrowser.open(url)
