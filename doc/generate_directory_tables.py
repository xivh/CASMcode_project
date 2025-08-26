# Use the data in "doc/directory_tables.json" to generate sections included in
# the project_structure.rst file.

import json


def escape_html_chars(input_string):
    """
    Escapes special HTML characters in a string.

    Args:
        input_string (str): The string to escape.

    Returns:
        str: The escaped string.
    """
    return input_string.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_file_row(file: dict, section: list[str]):
    """
    Generates a row for a file in the directory table.

    Args:
        file (dict): A dictionary containing file information.

    Returns:
        str: A formatted string representing the file row.
    """
    section.append("        <tr>")
    section.append(
        f"            <td><code>{escape_html_chars(file['name'])}</code></td>"
    )
    section.append(f"            <td>{escape_html_chars(file['description'])}</td>")
    if file["format"]["text"] == "link-icon":
        section.append(
            f"            <td><a class=\"only-light reference internal image-reference\" href=\"{escape_html_chars(file['format']['href'])}\"><img alt=\"link icon\" class=\"only-light\" src=\"../_static/link-16.svg\"></a>"
        )
        section.append(
            f"            <a class=\"only-dark reference internal image-reference\" href=\"{escape_html_chars(file['format']['href'])}\"><img alt=\"link icon\" class=\"only-dark\" src=\"../_static/link-16-dark.svg\"></a>"
        )
    else:
        section.append(
            f"            <td><a href=\"{escape_html_chars(file['format']['href'])}\">{escape_html_chars(file['format']['text'])}</a></td>"
        )
    section.append("        </tr>")


def generate_section(data):
    section = []
    section.append(f".. _{escape_html_chars(data['anchor'])}:\n")

    # Section Header
    section.append(
        f"{escape_html_chars(data['section'])}\n{'^' * len(data['section'])}\n"
    )

    # Begin List
    section.append('.. raw:: html\n\n    <dl class="casm-list">')

    # Location
    section.append(
        f'    <div style="display: flex; flex-direction: row; align-items: center; gap: 5px;">'
    )
    section.append(f'        <dt class="casm-part">Location:</dt>')
    section.append(
        f"        <dd class=\"casm-part\"><code>{escape_html_chars(data['location'])}</code></dd>"
    )
    section.append("    </div>")

    # Contents
    section.append('    <dt class="casm-part">Contents:</dt>')
    section.append('    <dd class="casm-part">')
    section.append('    <table class="casm-table">')
    section.append("        <tr>")
    section.append("            <th>Name</th>")
    section.append("            <th>Description</th>")
    section.append("            <th>Format</th>")
    section.append("        </tr>")
    for file in data["files"]:
        generate_file_row(file=file, section=section)
    section.append("    </table>")
    section.append("    </dd>")

    # Contents (Deprecated)
    if "deprecated_files" in data:
        section.append('    <dt class="casm-part">Deprecated contents:</dt>')
        section.append('    <dd class="casm-part">')
        section.append('    <table class="casm-table">')
        section.append("        <tr>")
        section.append("            <th>Name</th>")
        section.append("            <th>Description</th>")
        section.append("            <th>Format</th>")
        section.append("        </tr>")
        for file in data["deprecated_files"]:
            generate_file_row(file=file, section=section)
        section.append("    </table>")
        section.append("    </dd>")

    # End list
    section.append("    </dl>")
    return "\n".join(section)


# Example usage
with open("doc/directory_tables.json", "r") as f:
    json_data = json.load(f)

with open("doc/usage/project_structure_tables.rst", "w") as rst_file:
    for section_data in json_data:
        section = generate_section(section_data)
        rst_file.write(section + "\n\n")
