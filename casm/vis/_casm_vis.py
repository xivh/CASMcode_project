#!/usr/bin/env python3

import os
import platform
import signal
import subprocess
import time
import typing
import webbrowser

from ._functions import get_config, get_pid_file

config = get_config()


def run_server(script, port):
    """Run a server using gunicorn."""
    command = [
        "gunicorn",
        "-w",
        "4",
        "--worker-class",
        "gthread",
        "--worker-tmp-dir",
        "/tmp",
        "-b",
        f"localhost:{port}",
        script,
    ]
    env = os.environ.copy()
    if platform.system() == "Darwin":
        env["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
    return subprocess.Popen(command, start_new_session=True, env=env)


def run_bokeh_server():
    """Run the Bokeh server."""
    command = ["casm-bokeh-server"]
    return subprocess.Popen(command, start_new_session=True)


def _start_casmvis(
    server_names: typing.Optional[list[str]] = None,
    browser: bool = True,
):
    """Start the casm-vis servers if not already running.

    Parameters
    ----------
    server_names : Optional[list[str]], optional
        List of server names to start. Options are "bokeh", "api", "vis", or "all".
        If None, all servers will be started. Default is None.
    """

    if server_names is None:
        server_names = ["all"]
    elif len(server_names) == 0 and not browser:
        print("Nothing requested.")
        return

    start_bokeh = "all" in server_names or "bokeh" in server_names
    start_api = "all" in server_names or "api" in server_names
    start_vis = "all" in server_names or "vis" in server_names

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
            if ("all" in server_names or name in server_names) and pid != 0:
                try:
                    # Check if the process with the PID is running
                    import os

                    os.kill(pid, 0)
                    print(f"casm-vis {name} server already running with PID {pid}.")

                except OSError:
                    print(f"casm-vis {name} server with PID {pid} is not running.")
                    servers[name] = 0

    if start_bokeh and servers["bokeh"] == 0:
        print("Starting CASM Bokeh server...")
        _bokeh_server_process = run_bokeh_server()
        time.sleep(0.2)
        servers["bokeh"] = _bokeh_server_process.pid
    if start_api and servers["api"] == 0:
        api_url = config["CASMVIS_API_SERVER"]
        api_port = int(api_url.split(":")[-1])
        print("Starting CASM API server...")
        _api_server_process = run_server("casm.vis._api_server:app", api_port)
        time.sleep(0.2)
        servers["api"] = _api_server_process.pid
    if start_vis and servers["vis"] == 0:
        vis_url = config["CASMVIS_SERVER"]
        vis_port = int(vis_url.split(":")[-1])
        print("Starting CASM VIS server...")
        _vis_server_process = run_server("casm.vis._vis_server:app", vis_port)
        time.sleep(0.2)
        servers["vis"] = _vis_server_process.pid

    # Any PIDs set to 0 should be removed from the dictionary:
    servers = {name: pid for name, pid in servers.items() if pid != 0}

    # Write the PIDs to the PID file
    with open(pid_file, "w") as f:
        for name, pid in servers.items():
            f.write(f"{name} {pid}\n")

    # print("All CASM VIS servers started.")
    if browser:
        print(f"Opening casm-vis ({config['CASMVIS_SERVER']}) in your browser...")
        webbrowser.open(config["CASMVIS_SERVER"])
    else:
        print(
            f"To open casm-vis, navigate to {config['CASMVIS_SERVER']} in your browser."
        )


def stop(
    server_names: typing.Optional[list[str]] = None,
):
    """Stop the casm-vis servers if running.

    Parameters
    ----------
    server_names : Optional[list[str]], optional
        List of server names to stop. Options are "bokeh", "api", "vis", or "all".
        If None, all servers will be stopped. Default is None.
    """
    if server_names is None:
        server_names = ["all"]
    elif len(server_names) == 0:
        print("Nothing requested.")
        return

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

    deleted = []
    for name, pid in servers.items():
        if "all" not in server_names and name not in server_names:
            continue
        try:
            # Check if the process with the PID is running
            import os

            print(f"Terminating casm-vis {name} server with PID {pid}...")
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.2)
            deleted.append(name)
        except OSError:
            print(f"casm-vis {name} server with PID {pid} is not running.")

    for name in deleted:
        del servers[name]

    if len(servers) > 0:
        # Rewrite the PID file with the remaining servers
        with open(pid_file, "w") as f:
            for name, pid in servers.items():
                f.write(f"{name} {pid}\n")
    else:
        # Remove the PID file
        if pid_file.exists():
            pid_file.unlink()
            print("PID file removed.")
            time.sleep(0.2)

        print("All casm-vis servers stopped.")


def start(
    server_names: typing.Optional[list[str]] = None,
    browser: bool = True,
):
    """Start the casm-vis servers if not already running.

    Parameters
    ----------
    server_names : Optional[list[str]] = None
        List of server names to start. Options are "bokeh", "api", "vis", or "all".
        If None, all servers will be started. Default is None.
    browser : bool = True
        Whether to open casm-vis in the default web browser. Default is True.
    """
    _start_casmvis(
        server_names=server_names,
        browser=browser,
    )


def run_start(args):
    server_names = []
    if args.all:
        server_names.append("all")
    if args.bokeh:
        server_names.append("bokeh")
    if args.api:
        server_names.append("api")
    if args.vis:
        server_names.append("vis")

    _start_casmvis(
        server_names=server_names,
        browser=args.browser,
    )


def run_stop(args):
    server_names = []
    if args.all:
        server_names.append("all")
    if args.bokeh:
        server_names.append("bokeh")
    if args.api:
        server_names.append("api")
    if args.vis:
        server_names.append("vis")

    stop(
        server_names=server_names,
    )


def main():

    import argparse

    parser = argparse.ArgumentParser(
        prog="casm-vis", description="CASM visualization server management"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Start casm-vis servers")
    start_parser.set_defaults(func=run_start)
    start_parser.add_argument(
        "-a", "--all", action="store_true", help="Start all casm-vis servers."
    )
    start_parser.add_argument(
        "--bokeh", action="store_true", help="Start the Bokeh server."
    )
    start_parser.add_argument(
        "--api", action="store_true", help="Start the API server."
    )
    start_parser.add_argument(
        "--vis", action="store_true", help="Start the VIS server."
    )
    start_parser.add_argument(
        "-b",
        "--browser",
        action="store_true",
        help="Open casm-vis in the default browser.",
    )

    stop_parser = subparsers.add_parser("stop", help="Stop casm-vis servers")
    stop_parser.set_defaults(func=run_stop)
    stop_parser.add_argument(
        "-a", "--all", action="store_true", help="Stop all casm-vis servers."
    )
    stop_parser.add_argument(
        "--bokeh", action="store_true", help="Stop the Bokeh server only."
    )
    stop_parser.add_argument(
        "--api", action="store_true", help="Stop the API server only."
    )
    stop_parser.add_argument(
        "--vis", action="store_true", help="Stop the VIS server only."
    )

    args = parser.parse_args()

    args.func(args)


if __name__ == "__main__":
    main()
