#!/usr/bin/env python3

import signal
import subprocess
import time
import webbrowser

from ._functions import get_config, get_pid_file

config = get_config()


def run_server(script, port):
    """Run a server using gunicorn."""
    command = ["gunicorn", "-w", "4", "-b", f"localhost:{port}", script]
    return subprocess.Popen(command)


def run_bokeh_server():
    """Run the Bokeh server."""
    command = ["casm-bokeh-server"]
    return subprocess.Popen(command)


def _start_casmvis():

    servers = dict(
        bokeh=0,
        api=0,
        vis=0,
    )

    pid_file = get_pid_file()

    # Use PID file to check if the servers are already running:
    if pid_file.exists():
        with open(pid_file, "r") as f:
            for line in f:
                if line.strip():
                    name, pid_str = line.split()
                    servers[name] = int(pid_str)

        for name, pid in servers.items():
            if pid != 0:
                try:
                    # Check if the process with the PID is running
                    import os

                    os.kill(pid, 0)
                    print(f"casm-vis {name} server already running with PID {pid}.")

                except OSError:
                    print(f"casm-vis {name} server with PID {pid} is not running.")
                    servers[name] = 0

    if servers["bokeh"] == 0:
        print("Starting CASM Bokeh server...")
        _bokeh_server_process = run_bokeh_server()
        time.sleep(0.2)
        servers["bokeh"] = _bokeh_server_process.pid
    if servers["api"] == 0:
        api_url = config["CASMVIS_API_SERVER"]
        api_port = int(api_url.split(":")[-1])
        print("Starting CASM API server...")
        _api_server_process = run_server("casm.vis._api_server:app", api_port)
        time.sleep(0.2)
        servers["api"] = _api_server_process.pid
    if servers["vis"] == 0:
        vis_url = config["CASMVIS_SERVER"]
        vis_port = int(vis_url.split(":")[-1])
        print("Starting CASM VIS server...")
        _vis_server_process = run_server("casm.vis._vis_server:app", vis_port)
        time.sleep(0.2)
        servers["vis"] = _vis_server_process.pid

    # Write the PIDs to the PID file
    with open(pid_file, "w") as f:
        for name, pid in servers.items():
            f.write(f"{name} {pid}\n")

    print("All CASM VIS servers started.")
    print(f"Opening casm-vis ({config['CASMVIS_SERVER']}) in your browser...")
    webbrowser.open(config["CASMVIS_SERVER"])


def stop():
    pid_file = get_pid_file()
    if not pid_file.exists():
        print("No PID file found. No servers are running.")
        return

    # Use PID file to check if the servers are already running:
    servers = dict()
    with open(pid_file, "r") as f:
        for line in f:
            if line.strip():
                name, pid_str = line.split()
                servers[name] = int(pid_str)

    for name, pid in servers.items():
        try:
            # Check if the process with the PID is running
            import os

            print(f"Terminating casm-vis {name} server with PID {pid}...")
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.2)
        except OSError:
            print(f"casm-vis {name} server with PID {pid} is not running.")

    # Remove the PID file
    if pid_file.exists():
        pid_file.unlink()
        print("PID file removed.")
        time.sleep(0.2)

    print("All CASM VIS servers stopped.")


def start():
    _start_casmvis()


def main():

    import argparse

    parser = argparse.ArgumentParser(
        prog="casm-vis", description="CASM VIS server management"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("start", help="Start CASM VIS servers")
    subparsers.add_parser("stop", help="Stop CASM VIS servers")

    args = parser.parse_args()

    if args.command == "start":
        _start_casmvis()

    elif args.command == "stop":
        stop()


if __name__ == "__main__":
    main()
