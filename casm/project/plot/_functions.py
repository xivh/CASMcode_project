def get_single_argument(doc, name):
    """Get query argument from the request."""
    value = doc.session_context.request.arguments.get(name)
    if value is None:
        raise ValueError(f"Error: missing argument '{name}'")
    elif len(value) != 1:
        raise ValueError(f"Error: multiple values for '{name}'")
    return value[0].decode("utf-8")
