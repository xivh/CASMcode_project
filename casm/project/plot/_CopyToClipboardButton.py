import typing

import bokeh.models
from bokeh.layouts import column

from ._DashboardStyles import DashboardStyles

ContentCopyOutlinedIcon_svg = (
    '<path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12zm3 4H8c-1.1 0-2 .9-2 2v14c0 '
    '1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2m0 16H8V7h11z"/>'
)
CheckCircleOutlineIcon_svg = (
    '<path d="M16.59 7.58L10 14.17l-3.59-3.58L5 12l5 5 8-8z M12 2C6.48 2 2 '
    "6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z m0 18c-4.42 "
    '0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z"/>'
)


class CopyToClipboardButton:
    """A button that copies something to the user's clipboard."""

    def __init__(
        self,
        label: str,
        source: bokeh.models.ColumnDataSource,
        snackbar_message: typing.Optional[str] = None,
        show_copy_icon: bool = False,
    ):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        label: str = "Copy path"
            The label to show on the button.

        source: bokeh.models.ColumnDataSource
            A ColumnDataSource that contains the data to be copied to the clipboard.
            Expected to have a column named 'text_to_copy' with the text to copy in the
            first row.

        snackbar_message: Optional[str] = None
            If provided, a snackbar will briefly appear with this message after the
            button is clicked. If None, no snackbar is shown.

        show_copy_icon: bool = False
            If True, a ContentCopyOutlinedIcon SVG icon is shown before the button
            label text.
        """
        self.source = source
        """bokeh.models.ColumnDataSource: The data source containing the text to copy
        to the clipboard.

        Expected to have a column named 'text_to_copy' with the text to copy in the
        first row."""

        self.label = label
        """str: The label to show on the button."""

        if snackbar_message is None:
            snackbar_message = "Copied to clipboard!"

        self.snackbar_message = snackbar_message
        """Optional[str]: If provided, a snackbar briefly appears with this message
        after the button is clicked."""

        self.show_copy_icon = show_copy_icon
        """bool: If True, a ContentCopyOutlinedIcon SVG icon is shown before the
        button label text."""

    def make_layout(
        self,
        styles: DashboardStyles = None,
    ):
        """Return the layout containing the button."""

        # 2. Create the button, optionally with a copy icon before the label
        button_kwargs = dict(label=self.label, button_type="success")
        if self.show_copy_icon:
            button_kwargs["icon"] = bokeh.models.SVGIcon(
                svg=(
                    '<svg viewBox="0 0 24 24" '
                    'xmlns="http://www.w3.org/2000/svg" fill="currentColor">'
                    f"{ContentCopyOutlinedIcon_svg}"
                    "</svg>"
                ),
                size="1.2em",
            )
        icon_button = bokeh.models.Button(**button_kwargs)

        # 3. Optionally create a snackbar Div (fixed-positioned, initially hidden)
        snackbar = None
        if self.snackbar_message is not None:
            snackbar = bokeh.models.Div(
                text=(
                    '<span style="display:flex; align-items:center;">'
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"'
                    ' width="18" height="18" fill="currentColor"'
                    ' style="margin-right:8px; flex-shrink:0;">'
                    f"{CheckCircleOutlineIcon_svg}"
                    "</svg>"
                    f"{self.snackbar_message}"
                    "</span>"
                ),
                visible=False,
                stylesheets=[bokeh.models.InlineStyleSheet(css="""
                        :host {
                            position: fixed;
                            bottom: 30px;
                            left: 5%;
                            z-index: 9999;
                            background-color: #323232;
                            color: white;
                            padding: 12px 24px;
                            border-radius: 4px;
                            font-size: 14px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                        }
                        """)],
            )

        # 4. Add your Clipboard JS logic
        if snackbar is not None:
            js_code = """
            const data = source.data['text_to_copy'][0];
            navigator.clipboard.writeText(data).then(() => {
                snackbar.visible = true;
                setTimeout(() => { snackbar.visible = false; }, 3000);
            });
            """
            icon_button.js_on_event(
                "button_click",
                bokeh.models.CustomJS(
                    args={"source": self.source, "snackbar": snackbar},
                    code=js_code,
                ),
            )
        else:
            js_code = """
            const data = source.data['text_to_copy'][0];
            navigator.clipboard.writeText(data).then(() => {});
            """
            icon_button.js_on_event(
                "button_click",
                bokeh.models.CustomJS(
                    args={"source": self.source},
                    code=js_code,
                ),
            )

        children = [icon_button]
        if snackbar is not None:
            children.append(snackbar)

        return column(
            *children,
            margin=(10, 0),
        )
