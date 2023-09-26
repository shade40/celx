![celx](https://github.com/shade40/celx/blob/main/assets/header.png?raw=true)

## celx

A modern terminal UI framework powered by hypermedia served over HTTP.

```
pip install sh40-celx
```

See [/server](https://github.com/shade40/celx/tree/main/server/) for an example server & app.

### Quickstart

`celx` is a TUI application framework inspired by [htmx](htmx.org). It emphasizes the usage of hypermedia
as the engine of application state (HATEOAS) as an alternative to reactive client-side frameworks. `celx` apps are
written as XML fragments, and communicated through the Hypertext Transfer Protocol (HTTP).

Let's start with a basic application index (running on `/`):

```xml
<celx version="0">
  <page>
    <tower eid="root">
      <row eid="header">
        <text>Hello World</text>
      </row>
      <tower eid="body">
        <text>This is the app's body</text>
        <button>Insert content</button>
      </tower>
    </tower>
  </page>
</tower>
```

At the moment, both the header and body will take equal amounts of space on the page. You probably don't want this,
so let's modify `header` to only take 1 cell of height:

```xml
<row eid="header">
  <style> height: 1 </style>
</row>
```

You can insert a `<style>` tag everywhere, and it is always scoped to its parent widget. In effect, this means the above
style gets converted to:

```yaml
Row#header:
  height: 1
```

You can insert `<style>` tags into the `page` and `celx` tags as well. We don't add a scoping header in such cases,
as those objects aren't selectable. `page` styles are local to the current page object, `celx` (app) styles are global
to all pages.

We use [Celadon](https://github.com/shade40/celadon) under the hood, so we inherit its selector & styling syntax. You can
set any (already defined) attributes of any selected widget. Let's make the app's button span the whole width using a local
style:

```xml
<button>
  Insert content
  <style> width: null </style>
</button>
```

Alternatively, you can use a pre-defined group to do the same:

```xml
<button group="width-fill">
  Insert content
</button>
```

#### Adding interactivity

You can press our button already, but you might notice it doesn't do anything. Let's fix that.

First, add an on-submit event to the button:

```xml
<button group="width-fill" on-submit="GET /content; swap in #body">
  Insert content
</button>
```

And let's add the corresponding endpoint to the server (running on `/content`):

```xml
<text>This is some cool content</text>
```

After this, our button will:

- Send an HTTP `GET` request to `/content`, keeping its result
- Parse the result as a widget, and swap `#body`'s children with it

The syntax used here is quite simple:

`<command> <arg1> <arg2> ...`

...where command is one of:

- `GET`
- `POST`
- `insert`
- `swap`
- `append`

`POST` optionally takes a selector for its first arg (`POST #parent /content`), which controls the
widget whos serialized result will be sent in the request. It defaults to the parent of the widget
executing the request (our button, in this case).

`insert`, `swap` and `append` take a location as their first argument, similar to `hx-swap`. Its
value must be one of:

- `in`: Add result into the targets children
- `before`: Add result _before_ the target (by essentially executing the command on the target's parent, offset
    by the target's offset)
- `after`: Add result _after_ the target (the same way)
- `None`: (only for `swap`) Replaces the target widget completely, deleting it from its parent and putting
    result in its place.

While `swap` replaces the target's (or its parent's) children completely (deleting previous content), `insert`
and `append` add onto the current list

So in effect, our text and button will disappear and get replaced by whatever our server returns.

![rule](https://singlecolorimage.com/get/707E8C/1600x3)

### Features

#### Hypermedia as the Engine of Application State

Since applications are served over HTTP, you don't have to write _any_ client side code. So why is that
a good thing?

- No client-side state duplication (your client doesn't even have to be _aware_ of state)

  You cannot (and should never) trust client side code. If your application state mutates on the
  client side, you must be able to validate it on the server, as the client could do _anything_
  with that state. This essentially means you have to have duplicated state, and validation on both
  sides.

  Since all of your state is on the server, you avoid most of these issues.

- You're free to choose your own server

  Don't like Python? You can use any HTTP server, in ANY language. Python is more than fast enough
  for our runtime, and this way all custom logic & slow operations happen on the server side in the
  language of your choosing.

- Instant usability, no need to install potentially dangerous application code

  Your users only need the celx runtime to run your application. From that point on, trying out a new
  app takes as much as writing in the URL its served at, and pressing enter. No further installation,
  no 'clone my repo, download my build tool and execute these commands', not even a `pip install`.

- Running a celx & html of the same backend on the same server

  Since every bit of state is handled on the backend, you can simply send out different formats to represent
  the same interfaces based on who is listening. In the (near) future celx will send a specific header
  to tell the server to send celx' XML instead of HTML.

#### A sophisticated styling engine

As shown above, each `<style>` tag is scoped to its parent widget. Think of this as a less error-prone
version of CSS' inline styles, or a more readable Tailwind. This approach doesn't fully replace the need
for Tailwind-like helper groups, so we have a few of those as well.

Our (or rather [Celadon](https://github.com/shade40/Celadon)'s) styling system is also pretty neat in
other ways. It supports nested styles, hierarchal queries for both direct and indirect parents, states
(CSS' pseudoclasses), as well as your basic CSS stuff like types, ids and classes (named 'groups' in our case).

Here is an example from Celadon's README. Most of this should feel fairly familiar if you're used to
working with CSS:

```yaml
Button:
    fill_style: '@ui.primary'
    # Automatically use either white or black, based on the W3C contrast
    # guidelines
    content_style: ''

    # On hover, become a bit brighter
    /hover: # Equivalent to 'Button/hover'
        fill_style: '@ui.primary+1'

    # Become a bit taller if in the 'big' group
    .big:
        height: 3

    # If part of a Row in the 'button-row' group, fill available width.
    # '&' stands for the selector in the previous nesting layer, `Button`
    # in this case.
    Row.button-row > &:
        width: null
```

![rule](https://singlecolorimage.com/get/4A7A9F/1600x3)

### Documentation

Once the shade40 suite gets to a settled state (near 1.0), documentation will be
hosted both online and as a celx application. Until then some of the widget references by using
`python3 -m pydoc <name>`.

We will also create some example server applications to get you started with.

![rule](https://singlecolorimage.com/get/AFE1AF/1600x3)

### See also

- [Hypermedia Systems](https://hypermedia.systems): The primary inspiration for the library. A great book, available
    as hard-copy, ebook or even for free.
- [Celadon](https://github.com/shade40/celadon): The core of the framework, providing the widget & styling
    systems and the application runtime
- [Zenith](https://github.com/shade40/zenith): The inline-markup language used by the framework, which can
    be used either directly in widgets `<text>[bold]Title</text>` or in style definitions `<style> content_style: bold </style>`.
- [Slate](https://github.com/shade40/slate): The engine powering every interaction we make to the terminal and
    its APIs, providing us with intelligent per-changed-character drawing and a way to color text (quite a useful
    feature!) 
