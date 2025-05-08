import pathlib
import typing

from bokeh.server.server import Server
from tornado.ioloop import IOLoop

import casm.vis

_server_manager = None


class ServerManager:
    """Manage multiple Bokeh applications on a single server."""

    def __init__(
        self,
        allow_websocket_origin: typing.Optional[list[str]] = None,
        allow_origin: typing.Optional[list[str]] = None,
    ):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        allow_websocket_origin: typing.Optional[list[str]] = None
            A list of allowed websocket origins. Default is:

            .. code-block:: python

                [
                    "localhost:5000", # casmvis server
                    "http://127.0.0.1:5000",
                    "localhost:5006", # casmbokeh server
                    "http://127.0.0.1:5006",
                ]


        """
        self._applications = {}
        self._server = None

        if allow_websocket_origin is None:
            config = casm.vis.get_config()
            casmvis_server = config["CASMVIS_SERVER"].split("://")[-1]
            api_server = config["CASMVIS_API_SERVER"].split("://")[-1]
            bokeh_server = config["CASMVIS_BOKEH_SERVER"].split("://")[-1]

            allow_websocket_origin = [
                casmvis_server,  # casmvis client
                api_server,  # casmvis client - dev
                bokeh_server,  # casmvis server
            ]
        self.allow_websocket_origin = allow_websocket_origin

        if allow_origin is None:
            allow_origin = allow_websocket_origin
        self.allow_origin = allow_origin

    def add_application(
        self,
        url: pathlib.Path,
        app: typing.Callable,
    ):
        """Add a new Bokeh application to the server.

        Parameters
        ----------
        url: pathlib.Path
            Example: "/configuration_set_dash"

        app: typing.Callable
            A function, `def app(doc)`, that modifies a Bokeh document.

        allow_websocket_origin: typing.Optional[list[str]] = None
            A list of allowed websocket origins.
        """
        self._applications[str(url)] = app

    def start(self, show=False):
        """Start the Bokeh server.

        Parameters
        ----------
        show: bool
            If True, open a browser window to the server.

        """
        config = casm.vis.get_config()
        url = config["CASMVIS_BOKEH_SERVER"]
        port = int(url.split(":")[-1])

        self._server = Server(
            self._applications,
            port=port,
            io_loop=IOLoop.current(),
            allow_websocket_origin=self.allow_websocket_origin,
            allow_origin=self.allow_origin,
        )

        self._server.start()
        if show:
            for url in self._applications:
                self._server.io_loop.add_callback(self._server.show, url)
        self._server.io_loop.start()


def add_application(
    url: pathlib.Path,
    app: typing.Callable,
):
    """Add a new Bokeh application to the server.


    Parameters
    ----------
    url: pathlib.Path
        Example: "/configuration_set_dash"
    app: typing.Callable
        A function, `def app(doc)`, that modifies a Bokeh document.
    """

    global _server_manager

    if _server_manager is None:
        _server_manager = ServerManager()
    _server_manager.add_application(url=url, app=app)


def start_applications(show=False):
    """Start the Bokeh server with all added applications.

    Parameters
    ----------
    show: bool
        If True, open a browser window to the server.
    """
    global _server_manager

    if _server_manager is not None:
        _server_manager.start(show=show)
    else:
        raise RuntimeError("No applications to start.")
