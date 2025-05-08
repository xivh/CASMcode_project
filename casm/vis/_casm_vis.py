#!/usr/bin/env python3

import subprocess
import time
import webbrowser

from casm.vis import get_config

config = get_config()


def run_server(script, port):
    """Run a server using gunicorn."""
    command = ["gunicorn", "-w", "4", "-b", f"localhost:{port}", script]
    return subprocess.Popen(command)


def run_bokeh_server():
    """Run the Bokeh server."""
    command = ["casm-bokeh-server"]
    return subprocess.Popen(command)


def main():
    # Run the _bokeh_server.py
    bokeh_url = config["CASMVIS_BOKEH_SERVER"]
    print(f"Starting the CASM Bokeh server ({bokeh_url})...")
    bokeh_server = run_bokeh_server()
    time.sleep(0.2)

    # Run the _api_server.py
    api_url = config["CASMVIS_API_SERVER"]
    api_port = int(api_url.split(":")[-1])
    print(f"Starting the CASM API server ({api_url})...")
    api_server = run_server("casm.vis._api_server:app", api_port)
    time.sleep(0.2)

    # Run the _vis_server.py
    vis_url = config["CASMVIS_SERVER"]
    vis_port = int(vis_url.split(":")[-1])
    print(f"Starting the casm-vis server ({vis_url}) ...")
    vis_server = run_server("casm.vis._vis_server:app", vis_port)
    time.sleep(0.2)

    print(f"Opening casm-vis ({vis_url}) in your browser...")
    webbrowser.open(vis_url)
    print("Press Ctrl+C to terminate all servers.")
    print()

    try:
        # Wait for the servers to run
        bokeh_server.wait()
        api_server.wait()
        vis_server.wait()
    except KeyboardInterrupt:
        # Terminate all servers on Ctrl+C
        bokeh_server.terminate()
        api_server.terminate()
        vis_server.terminate()


if __name__ == "__main__":
    main()
