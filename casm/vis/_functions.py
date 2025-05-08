import os
import pathlib

root = pathlib.Path(os.environ["HOME"]) / ".casmvis"

default_config = {
    "CASMVIS_SERVER": "http://localhost:3000",
    "CASMVIS_BOKEH_SERVER": "http://localhost:3002",
    "CASMVIS_API_SERVER": "http://localhost:3001",
}


def get_config():
    """Get casm-vis configuration variables.

    Returns
    -------
    config: dict
        A dictionary with the following keys:
        - CASMVIS_BOKEH_SERVER: str
            The URL of the CASM Bokeh server.
        - CASMVIS_API_SERVER: str
            The URL of the CASM API server.

    """
    from casm.project.json_io import read_required
    from libcasm.xtal import pretty_json

    config_file = root / "config.json"
    if not config_file.exists():
        # Create the config file with default values
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w") as f:
            f.write(pretty_json(default_config))
        return default_config

    return read_required(path=config_file)


def get_required_argument(doc, name):
    """Get query argument from the request."""
    value = doc.session_context.request.arguments.get(name)
    if value is None:
        raise ValueError(f"Error: missing argument '{name}'")
    elif len(value) != 1:
        raise ValueError(f"Error: multiple values for '{name}'")
    return value[0].decode("utf-8")


def get_optional_argument(doc, name, default=None):
    """Get optional query argument from the request."""
    value = doc.session_context.request.arguments.get(name)
    if value is None:
        return default
    elif len(value) != 1:
        raise ValueError(f"Error: multiple values for '{name}'")
    return value[0].decode("utf-8") or default
