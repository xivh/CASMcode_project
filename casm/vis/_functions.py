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
