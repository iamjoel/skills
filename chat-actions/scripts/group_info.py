import re
from collections.abc import Callable
from html import escape
from html.parser import HTMLParser


DISPLAY_TAGS = frozenset({
    "article", "aside", "b", "blockquote", "br", "code", "dd", "div", "dl", "dt",
    "em", "figcaption", "figure", "footer", "h1", "h2", "h3", "h4", "h5", "h6",
    "header", "hr", "i", "kbd", "li", "mark", "ol", "output", "p", "pre",
    "progress", "s", "section", "small", "span", "strong", "sub", "sup", "time", "ul",
})
DISPLAY_ATTRIBUTES = frozenset({
    "aria-hidden", "aria-label", "class", "title", "data-progress-value", "data-progress-max",
    "data-progress-yellow-min", "data-progress-yellow-max",
})
VOID_TAGS = frozenset({"br", "hr"})
TEXT_BOUNDARIES = frozenset({
    "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "figcaption",
    "figure", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li",
    "ol", "p", "pre", "section", "ul",
})
BLOCKED_CONTENT_TAGS = frozenset({
    "audio", "canvas", "iframe", "math", "noscript", "object", "script", "style", "svg",
    "template", "textarea", "title", "video", "xmp",
})
VARIABLE = re.compile(r"\{[\w.-]+\}", re.ASCII)


class _GroupInfoParser(HTMLParser):
    def __init__(self, substitute: Callable[[str], str]):
        super().__init__(convert_charrefs=True)
        self.substitute = substitute
        self.markup: list[str] = []
        self.text: list[str] = []
        self.open_tags: list[str] = []
        self.blocked_tags: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in BLOCKED_CONTENT_TAGS:
            self.blocked_tags.append(tag)
            return
        if self.blocked_tags or tag not in DISPLAY_TAGS:
            return

        allowed_attrs = "".join(
            f' {name}="{escape(value)}"'
            for name, value in dict(attrs).items()
            if name in DISPLAY_ATTRIBUTES and value is not None
        )
        self.markup.append(f"<{tag}{allowed_attrs}>")
        if tag not in VOID_TAGS:
            self.open_tags.append(tag)
        if tag in TEXT_BOUNDARIES:
            self.text.append(" ")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in {"script", "style"}:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.blocked_tags:
            if tag in self.blocked_tags:
                while self.blocked_tags.pop() != tag:
                    pass
            return
        if tag in self.open_tags:
            while self.close_tag() != tag:
                pass

    def handle_data(self, data):
        if self.blocked_tags:
            return
        if VARIABLE.search(data):
            value = self.substitute(data)
            self.markup.append(f'<span data-group-info="{escape(data)}">{escape(value)}</span>')
        else:
            value = data
            self.markup.append(escape(value))
        self.text.append(value)

    def close_tag(self):
        tag = self.open_tags.pop()
        self.markup.append(f"</{tag}>")
        if tag in TEXT_BOUNDARIES:
            self.text.append(" ")
        return tag

    def result(self):
        while self.open_tags:
            self.close_tag()
        return "".join(self.markup), " ".join("".join(self.text).split())


def render_group_html(source: str, substitute: Callable[[str], str]) -> tuple[str, str]:
    parser = _GroupInfoParser(substitute)
    try:
        parser.feed(source)
        parser.close()
    except (AssertionError, NotImplementedError):
        # Malformed marked declarations can stop HTMLParser; retain only the reconstructed prefix.
        pass
    return parser.result()
