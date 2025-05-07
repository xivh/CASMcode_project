#!/usr/bin/env python3

import subprocess
import time
import webbrowser


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
    print("Starting the CASM Bokeh server (localhost:5006) ...")
    bokeh_server = run_bokeh_server()
    time.sleep(0.2)

    # Run the _api_server.py
    print("Starting the CASM API server (localhost:5000) ...")
    api_port = 5000
    api_server = run_server("casm.vis._api_server:app", api_port)
    time.sleep(0.2)

    # Run the _vis_server.py
    print("Starting the casm-vis server (localhost:3010) ...")
    ui_port = 3010
    vis_server = run_server("casm.vis._vis_server:app", ui_port)
    time.sleep(0.2)

    print("Opening casm-vis (http://localhost:3010/casm) in your browser...")
    webbrowser.open(f"http://localhost:{ui_port}/casm")
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
