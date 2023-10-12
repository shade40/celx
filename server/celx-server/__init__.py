import os

from flask import Flask, Response, request

LOREM = """\
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vestibulum in metus
suscipit, luctus augue vel, fringilla erat. Nulla at turpis volutpat,
porttitor lectus eu, malesuada eros. Phasellus at tortor libero. Class
aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos
himenaeos. Nam pellentesque dolor a scelerisque feugiat. Duis nec ante mi.
Integer in tortor elementum, imperdiet nunc sed, tincidunt erat. Sed non mi
accumsan, aliquet ante convallis, vulputate velit. Nullam malesuada nisl
ligula, ut fermentum risus tincidunt at. Vivamus sollicitudin condimentum
maximus. Etiam eu metus rhoncus, placerat orci ut, rutrum lorem.

Aliquam at laoreet ipsum. In vitae ante eu eros consectetur porta.
Curabitur euismod, massa in tempor convallis, neque quam elementum sem, eu
ultrices ex odio sed tellus. Curabitur ac ligula dignissim, lobortis lectus
vel, condimentum risus. Praesent quis accumsan tortor, vitae aliquam neque.
Maecenas id fermentum ex. Etiam enim purus, viverra et elementum vitae,
egestas et libero. Etiam vel lacus imperdiet, viverra purus quis, posuere
justo. Duis eu ex suscipit nisi hendrerit varius auctor id metus. Nullam
quis sollicitudin nibh. Nam eleifend pellentesque sodales. Vestibulum
ullamcorper vulputate euismod.

Curabitur ultrices commodo metus, suscipit varius velit. Nam sem tortor,
volutpat id sagittis at, cursus in purus. Fusce pretium, tellus non ultrices
feugiat, mauris purus condimentum lacus, id vestibulum eros velit vel orci.
Praesent gravida turpis et feugiat placerat. Sed at tellus congue, semper
diam aliquam, elementum ipsum. Nam eu libero lobortis, consectetur erat ege,
viverra est. Donec ultricies velit at dui egestas ultricies. Suspendisse
gravida velit non interdum sodales. Donec finibus ac velit non facilisis.
Praesent ipsum neque, malesuada ut laoreet sit amet, eleifend aliquet quam.
Fusce ex nibh, fringilla a augue eget, tristique lacinia ligula. Ut eu
tortor non dolor ultrices hendrerit eget non lectus. Mauris pharetra dolor
sit amet ante pellentesque sagittis. Praesent in ultricies odio, eu laoreet
felis.

In a augue sollicitudin felis commodo sollicitudin nec vel nibh. Nunc
euismod semper massa, in finibus enim lacinia consectetur. Ut tristique
risus augue, in mollis elit sodales at. Donec sed ipsum ligula. Praesent
suscipit neque ut faucibus euismod. Duis pellentesque ac enim eu ornare.
Curabitur blandit, velit ut luctus semper, erat sapien fermentum velit, a
sodales leo arcu nec est.

Morbi rutrum in est vitae placerat. Orci varius natoque penatibus et magnis
dis parturient montes, nascetur ridiculus mus. Nullam congue non mi at
malesuada. Nulla velit dui, iaculis in viverra id, facilisis at nibh. In
quis metus a erat lacinia porttitor sed vitae elit. Vivamus scelerisque
sagittis ex, quis scelerisque leo consectetur eget. Nunc sed sodales mi.
Nunc viverra dui eget erat accumsan, id placerat ligula consectetur. Sed
elementum dictum tortor ultrices aliquet. Proin ullamcorper euismod congue.
Nullam eleifend lacus euismod ante mattis sagittis. Phasellus eu erat mauri.

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vestibulum in metus
suscipit, luctus augue vel, fringilla erat. Nulla at turpis volutpat,
porttitor lectus eu, malesuada eros. Phasellus at tortor libero. Class
aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos
himenaeos. Nam pellentesque dolor a scelerisque feugiat. Duis nec ante mi.
Integer in tortor elementum, imperdiet nunc sed, tincidunt erat. Sed non mi
accumsan, aliquet ante convallis, vulputate velit. Nullam malesuada nisl
ligula, ut fermentum risus tincidunt at. Vivamus sollicitudin condimentum
maximus. Etiam eu metus rhoncus, placerat orci ut, rutrum lorem.
Aliquam at laoreet ipsum. In vitae ante eu eros consectetur porta.
Curabitur euismod, massa in tempor convallis, neque quam elementum sem, eu
ultrices ex odio sed tellus. Curabitur ac ligula dignissim, lobortis lectus
vel, condimentum risus. Praesent quis accumsan tortor, vitae aliquam neque.
Maecenas id fermentum ex. Etiam enim purus, viverra et elementum vitae,
egestas et libero. Etiam vel lacus imperdiet, viverra purus quis, posuere
justo. Duis eu ex suscipit nisi hendrerit varius auctor id metus. Nullam
quis sollicitudin nibh. Nam eleifend pellentesque sodales. Vestibulum
ullamcorper vulputate euismod.

Curabitur ultrices commodo metus, suscipit varius velit. Nam sem tortor,
volutpat id sagittis at, cursus in purus. Fusce pretium, tellus non ultrices
feugiat, mauris purus condimentum lacus, id vestibulum eros velit vel orci.
Praesent gravida turpis et feugiat placerat. Sed at tellus congue, semper
diam aliquam, elementum ipsum. Nam eu libero lobortis, consectetur erat ege,
viverra est. Donec ultricies velit at dui egestas ultricies. Suspendisse
gravida velit non interdum sodales. Donec finibus ac velit non facilisis.
Praesent ipsum neque, malesuada ut laoreet sit amet, eleifend aliquet quam.
Fusce ex nibh, fringilla a augue eget, tristique lacinia ligula. Ut eu
tortor non dolor ultrices hendrerit eget non lectus. Mauris pharetra dolor
sit amet ante pellentesque sagittis. Praesent in ultricies odio, eu laoreet
felis.

In a augue sollicitudin felis commodo sollicitudin nec vel nibh. Nunc
euismod semper massa, in finibus enim lacinia consectetur. Ut tristique
risus augue, in mollis elit sodales at. Donec sed ipsum ligula. Praesent
suscipit neque ut faucibus euismod. Duis pellentesque ac enim eu ornare.
Curabitur blandit, velit ut luctus semper, erat sapien fermentum velit, a
sodales leo arcu nec est.

Morbi rutrum in est vitae placerat. Orci varius natoque penatibus et magnis
dis parturient montes, nascetur ridiculus mus. Nullam congue non mi at
malesuada. Nulla velit dui, iaculis in viverra id, facilisis at nibh. In
quis metus a erat lacinia porttitor sed vitae elit. Vivamus scelerisque
sagittis ex, quis scelerisque leo consectetur eget. Nunc sed sodales mi.
Nunc viverra dui eget erat accumsan, id placerat ligula consectetur. Sed
elementum dictum tortor ultrices aliquet. Proin ullamcorper euismod congue.
Nullam eleifend lacus euismod ante mattis sagittis. Phasellus eu erat mauri.
"""

link = "ui.primary"

PAGE = f"""
<celx version='0'>
    <page title='{{title}}'>
        <styles>
            Text:
                .pad:
                    width: null

            Tower:
                '#root':
                    alignment: [center, center]
                    frame: padded

            Row#header:
                height: 2
                gap: 3
                fallback_gap: 3

            Link:
                content_style: {link}

                /hover:
                    content_style: {link} bold

                .active:
                    content_style: {link} underline

                    /hover:
                        content_style: {link} underline bold
        </styles>
        <tower eid='root'>
            <row eid='header'>
                <link eid="title" to="/">[bold]❒ Welcome! ❒[/]</link>
                <text group="pad">[white]</text>
                <link {{about}}>About</link>
                <link {{blog}}>Blog</link>
                <link {{form}}>Form</link>
                <link {{buttons}}>Buttons</link>
            </row>
            <tower eid='body' group="center">
{{body}}
            </tower>
        </tower>
    </page>
</celx>
"""

VALUE = [""]


def create_page(body: str, subpage: str | None = None) -> Response:
    title = (subpage or "").title()

    subpages = {page: "" for page in ["about", "blog", "form", "buttons"]} | {
        subpage: 'group="active"'
    }

    return Response(
        PAGE.format(title=title, body=body, **subpages), mimetype="text/xml"
    )


def create_app(test_config=None):
    app = Flask(__name__)

    @app.route("/")
    def index():
        return create_page(
            """
        <styles>
            alignment: [center, center]
        </styles>
        <text>This is the index</text>
        <lua> test = "hello" </lua>
        <row>
            <styles> height: 3 </styles>
            <lua> count = 5 </lua>
            <button eid='hey'>
                Counter: $outer.count $outer.outer.test
                <lua src="/static/counter.lua"></lua>
            </button>
            <text eid='hoo'>Counter: $outer.count</text>
        </row>
        """
        )

    @app.route("/about")
    def about():
        return create_page("<text>This is the about page</text>", subpage="about")

    @app.route("/blog")
    def blog():
        return create_page(
            f"""
            <styles> alignment: [center, center] </styles>
            <text>
                This is actually a blog
                <styles>
                    content_style: bold !gradient(76)
                    height: 2
                </styles>
            </text>
            <text groups="h-fill of-auto">
                {LOREM}
            </text>
            """,
            subpage="blog",
        )

    prompt = """
    <row group="prompt">
        <text> {text}: </text>
        <field name="{name}" placeholder="{text}..."></field>
    </row>
    """

    @app.route("/questions", methods=["GET", "POST"])
    def questions():
        if request.method == "GET":
            return Response(
                f"""
                <tower eid="questions">
                    {prompt.format(text="Username", name="username")}
                    {prompt.format(text="Password", name="password")}
                    <checkbox name="question-1">Question 1</checkbox>
                    <checkbox name="question-2">Question 2</checkbox>
                    <checkbox name="question-3">Question 3</checkbox>
                </tower>
                """,
                mimetype="text/xml",
            )

        data = request.get_json()

        return Response(
            f'<text groups="h-fill">{request.get_json()}</text>', mimetype="text/xml"
        )

    @app.route("/form")
    def form():
        return create_page(
            f"""
            <tower eid="questions">
                <styles>
                    gap: 1

                    frame: light

                    width: 0.6
                    height: 0.5

                    '> Checkbox':
                        height: 1

                    '> .prompt':
                        height: 1
                </styles>
            </tower>
            <tower eid="results">
                <styles> height: 1 </styles>
            </tower>
            <row group="center">
                <button on-submit='POST #questions /questions; swap in #results'>
                    Submit
                </button>
                <button on-submit='GET /questions; swap #questions'>Load</button>
                <styles> height: 1 </styles>
            </row>""",
            subpage="form",
        )

    @app.route("/new-button")
    def new_button():
        import time

        time.sleep(1)

        return f"<button>{time.strftime('%c')}</button>"

    @app.route("/buttons")
    def buttons():
        return create_page(
            """
            <tower eid="result" group="center"></tower>
            <button on-submit="GET /new-button; insert in #result">Insert New</button>
            """,
            subpage="buttons",
        )

    @app.route("/tiles")
    def tiles():
        tile = """\
        <text>
            [0]
            <styles>
                width: 10
                height: 5
                fill_style: "@{color}"
            </styles>
        </text>"""

        return create_page(
            f"""
            <tower>
                <styles>
                    gap: 1
                    fallback_gap: 1
                    frame: padded
                    fill_style: '@#22272F'

                    '> .color-row':
                        fill_style: '@#22272F'

                        gap: 1
                        fallback_gap: 1
                        height: 5

                </styles>
                <row group='color-row'>
                    {tile.format(color='celadon')}
                    {tile.format(color='zenith')}
                    {tile.format(color='slate')}
                </row>
                <row group='color-row'>
                    {tile.format(color='slate')}
                    {tile.format(color='celadon')}
                    {tile.format(color='zenith')}
                </row>
                <row group='color-row'>
                    {tile.format(color='zenith')}
                    {tile.format(color='slate')}
                    {tile.format(color='celadon')}
                </row>
            </tower>"""
        )

    @app.route("/grid")
    def grid():
        buttons = "\n".join("<button group='fill'>test</button>" for _ in range(10))
        return create_page("\n".join(f"<row>{buttons}</row>" for _ in range(10)))

    return app
