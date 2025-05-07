import bokeh.models


class DashboardStyles:
    def __init__(self):
        # -- Dark theme --
        self.darkstyle = bokeh.models.GlobalInlineStyleSheet(
            css="""
            * {
              font-family: roboto-mono;
            }

            @media (prefers-color-scheme: dark) {
              * {
                font-family: roboto-mono;
              }

              html {
                color-scheme: dark;
                color: #ddd;
              }
            }""",
        )

        self.dark_bk_input_style = bokeh.models.InlineStyleSheet(
            css="""
            @media (prefers-color-scheme: dark) {

            .bk-input {
              /* color: #bbb; */
              background-color:#222;
            }

            select:not([multiple]).bk-input, select:not([size]).bk-input {
              background-image: url('data:image/svg+xml;utf8,<svg version="1.1" viewBox="0 0 25 20" xmlns="http://www.w3.org/2000/svg"><path d="M 0,0 25,0 12.5,20 Z" fill="white" /></svg>');
            }

            .bk-input-group > .bk-spin-wrapper > .bk-spin-btn.bk-spin-btn-up:before {
              border-bottom: 5px solid white;
            }

            .bk-input-group > .bk-spin-wrapper > .bk-spin-btn.bk-spin-btn-down:before {
              border-top: 5px solid white;
            }

            .bk-btn-default {
              color: #ddd;
              background-color: #222;
              border-color: #ccc;
            }
            }
            """,  # noqa: E501
        )
