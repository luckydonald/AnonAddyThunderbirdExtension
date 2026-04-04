from __future__ import annotations

import importlib.util
import os
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "git" / "remote"
MODULE_PATH = ROOT / "git_remote_fix.py"
SPEC = importlib.util.spec_from_file_location("git_remote_fix", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeEvent:
    def __init__(self, app) -> None:
        self.app = app


class FakeBufferEvent:
    def __init__(self) -> None:
        self._callbacks = []

    def __iadd__(self, callback):
        self._callbacks.append(callback)
        return self

    def fire(self, buffer) -> None:
        for callback in list(self._callbacks):
            callback(buffer)


class FakeBuffer:
    def __init__(self, *, multiline: bool = False) -> None:
        self.multiline = multiline
        self._text = ""
        self.cursor_position = 0
        self.on_text_changed = FakeBufferEvent()

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        self._text = value
        self.cursor_position = min(self.cursor_position, len(value))
        self.on_text_changed.fire(self)


class FakeCondition:
    def __init__(self, func):
        self.func = func

    def __call__(self) -> bool:
        return bool(self.func())


@dataclass
class FakeBinding:
    key: str
    filter: FakeCondition | None
    handler: object


class FakeKeyBindings:
    def __init__(self) -> None:
        self.bindings: list[FakeBinding] = []

    def add(self, key: str, filter=None):
        def decorator(func):
            self.bindings.append(FakeBinding(key=key, filter=filter, handler=func))
            return func

        return decorator


class FakeFormattedTextControl:
    def __init__(self, text, focusable: bool = False) -> None:
        self.text = text
        self.focusable = focusable

    def fragments(self):
        return self.text() if callable(self.text) else self.text


class FakeBufferControl:
    def __init__(self, buffer: FakeBuffer, focusable: bool = True) -> None:
        self.buffer = buffer
        self.focusable = focusable


class FakeDimension:
    def __init__(self, preferred=None, min=None, max=None) -> None:
        self.preferred = preferred
        self.min = min
        self.max = max


class FakeWindow:
    def __init__(
        self,
        content=None,
        width=None,
        height=None,
        wrap_lines=None,
        dont_extend_width=None,
        always_hide_cursor=None,
        char=None,
    ) -> None:
        self.content = content
        self.width = width
        self.height = height
        self.wrap_lines = wrap_lines
        self.dont_extend_width = dont_extend_width
        self.always_hide_cursor = always_hide_cursor
        self.char = char


class FakeHSplit:
    def __init__(self, children, height=None) -> None:
        self.children = children
        self.height = height


class FakeVSplit:
    def __init__(self, children, height=None) -> None:
        self.children = children
        self.height = height


class FakeDynamicContainer:
    def __init__(self, get_container) -> None:
        self.get_container = get_container


class FakeLayout:
    def __init__(self, container, focused_element) -> None:
        self.container = container
        self.current_window = focused_element

    def focus(self, window) -> None:
        self.current_window = window

    def has_focus(self, window) -> bool:
        return self.current_window is window


class FakeStyle:
    def __init__(self, style_rules: dict[str, str]) -> None:
        self.style_rules = style_rules

    @classmethod
    def from_dict(cls, mapping: dict[str, str]):
        return cls(mapping)


class FakePromptToolkitRuntime:
    def __init__(self) -> None:
        self.current_app = None


class FakeRenderer:
    def __init__(self) -> None:
        self.clear_count = 0
        self.output = OutputRecorder()

    def clear(self) -> None:
        self.clear_count += 1


class OutputRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def clear(self) -> None:
        self.calls.clear()

    def cursor_goto(self, row: int = 0, column: int = 0) -> None:
        self.calls.append(("cursor_goto", row, column))

    def cursor_up(self, amount: int) -> None:
        self.calls.append(("cursor_up", amount))

    def cursor_down(self, amount: int) -> None:
        self.calls.append(("cursor_down", amount))

    def cursor_forward(self, amount: int) -> None:
        self.calls.append(("cursor_forward", amount))

    def cursor_backward(self, amount: int) -> None:
        self.calls.append(("cursor_backward", amount))

    def erase_end_of_line(self) -> None:
        self.calls.append(("erase_end_of_line",))

    def write(self, text: str) -> None:
        self.calls.append(("write", text))

    def write_raw(self, text: str) -> None:
        self.calls.append(("write_raw", text))

    def flush(self) -> None:
        self.calls.append(("flush",))


class FakeApplication:
    def __init__(
        self,
        *,
        layout,
        key_bindings,
        style,
        full_screen,
        mouse_support,
        refresh_interval=None,
    ) -> None:
        self.layout = layout
        self.key_bindings = key_bindings
        self.style = style
        self.full_screen = full_screen
        self.mouse_support = mouse_support
        self.refresh_interval = refresh_interval
        self.exit_result = None
        self.invalidate_count = 0
        self.renderer = FakeRenderer()
        FAKE_RUNTIME.current_app = self

    def exit(self, result=None) -> None:
        self.exit_result = result

    def invalidate(self) -> None:
        self.invalidate_count += 1

    def press(self, key: str) -> None:
        for binding in self.key_bindings.bindings:
            if binding.key != key:
                continue
            if binding.filter is not None and not binding.filter():
                continue
            binding.handler(FakeEvent(self))
            return
        raise AssertionError(f"No active key binding for {key!r}")

    def run(self):
        return self


FAKE_RUNTIME = FakePromptToolkitRuntime()


def fake_get_app():
    return FAKE_RUNTIME.current_app


def fake_has_focus(window):
    return FakeCondition(lambda: FAKE_RUNTIME.current_app.layout.has_focus(window))


class FakePromptToolkitModules:
    MODULE_NAMES = (
        "prompt_toolkit",
        "prompt_toolkit.application",
        "prompt_toolkit.buffer",
        "prompt_toolkit.filters",
        "prompt_toolkit.formatted_text",
        "prompt_toolkit.key_binding",
        "prompt_toolkit.layout",
        "prompt_toolkit.layout.controls",
        "prompt_toolkit.layout.dimension",
        "prompt_toolkit.styles",
    )

    def __init__(self) -> None:
        self.previous = {}

    def install(self) -> None:
        for name in self.MODULE_NAMES:
            self.previous[name] = sys.modules.get(name)

        prompt_toolkit = types.ModuleType("prompt_toolkit")
        application = types.ModuleType("prompt_toolkit.application")
        buffer = types.ModuleType("prompt_toolkit.buffer")
        filters = types.ModuleType("prompt_toolkit.filters")
        formatted_text = types.ModuleType("prompt_toolkit.formatted_text")
        key_binding = types.ModuleType("prompt_toolkit.key_binding")
        layout = types.ModuleType("prompt_toolkit.layout")
        layout_controls = types.ModuleType("prompt_toolkit.layout.controls")
        layout_dimension = types.ModuleType("prompt_toolkit.layout.dimension")
        styles = types.ModuleType("prompt_toolkit.styles")

        application.Application = FakeApplication
        application.get_app = fake_get_app
        buffer.Buffer = FakeBuffer
        filters.Condition = FakeCondition
        filters.has_focus = fake_has_focus
        formatted_text.StyleAndTextTuples = list
        key_binding.KeyBindings = FakeKeyBindings
        layout.DynamicContainer = FakeDynamicContainer
        layout.HSplit = FakeHSplit
        layout.Layout = FakeLayout
        layout.VSplit = FakeVSplit
        layout.Window = FakeWindow
        layout_controls.BufferControl = FakeBufferControl
        layout_controls.FormattedTextControl = FakeFormattedTextControl
        layout_dimension.Dimension = FakeDimension
        styles.Style = FakeStyle

        sys.modules["prompt_toolkit"] = prompt_toolkit
        sys.modules["prompt_toolkit.application"] = application
        sys.modules["prompt_toolkit.buffer"] = buffer
        sys.modules["prompt_toolkit.filters"] = filters
        sys.modules["prompt_toolkit.formatted_text"] = formatted_text
        sys.modules["prompt_toolkit.key_binding"] = key_binding
        sys.modules["prompt_toolkit.layout"] = layout
        sys.modules["prompt_toolkit.layout.controls"] = layout_controls
        sys.modules["prompt_toolkit.layout.dimension"] = layout_dimension
        sys.modules["prompt_toolkit.styles"] = styles

    def uninstall(self) -> None:
        for name, previous in self.previous.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def flatten_fragments(fragments) -> str:
    return "".join(text for _, text in fragments)


def split_fragment_lines(fragments) -> list[list[tuple[str, str]]]:
    lines: list[list[tuple[str, str]]] = [[]]
    for style, text in fragments:
        parts = text.split("\n")
        for index, part in enumerate(parts):
            if part:
                lines[-1].append((style, part))
            if index != len(parts) - 1:
                lines.append([])
    if lines and not lines[-1]:
        lines.pop()
    return lines


def window_width(window) -> int:
    width = window.width
    if isinstance(width, int):
        return width
    if hasattr(width, "preferred") and width.preferred is not None:
        return width.preferred
    if hasattr(width, "min") and width.min is not None:
        return width.min
    return 0


def join_line_fragments(line: list[tuple[str, str]]) -> str:
    return "".join(text for _, text in line)


def render_node_lines(node, render_window_fragments) -> list[str]:
    if isinstance(node, FakeDynamicContainer):
        return render_node_lines(node.get_container(), render_window_fragments)
    if isinstance(node, FakeWindow):
        return [join_line_fragments(line) for line in split_fragment_lines(render_window_fragments(node))] or [""]
    if isinstance(node, FakeHSplit):
        lines: list[str] = []
        for child in node.children:
            lines.extend(render_node_lines(child, render_window_fragments))
        return lines
    if isinstance(node, FakeVSplit):
        child_lines = [render_node_lines(child, render_window_fragments) for child in node.children]
        height = max((len(lines) for lines in child_lines), default=0)
        rendered: list[str] = []
        for index in range(height):
            parts: list[str] = []
            for child, lines in zip(node.children, child_lines):
                line = lines[index] if index < len(lines) else ""
                width = window_width(child) if isinstance(child, FakeWindow) else len(line)
                parts.append(line.ljust(width))
            rendered.append("".join(parts))
        return rendered
    raise TypeError(f"Unsupported fake node: {type(node)!r}")


class FakeTuiHarness:
    def __init__(self, app) -> None:
        self.app = app
        self.edit_container = self.app.layout.container.get_container()
        self.edit_body = self.edit_container.children[0]
        self.footer_container = self.edit_container.children[1]
        self.input_container = self.edit_body.children[1]
        self.input_row = self.input_container.children[1]
        self.username_window = self.input_row.children[1]
        self.tree_window = self.edit_body.children[4]
        self.actions_window = self.edit_body.children[6]
        self.status_window = self.edit_body.children[8]
        self.submit_window = self.edit_body.children[9]
        self.help_window = self.footer_container.children[0]

    def press(self, key: str, *, times: int = 1) -> None:
        for _ in range(times):
            self.app.press(key)

    def iter_windows(self, node=None):
        node = self.app.layout.container if node is None else node
        if isinstance(node, FakeDynamicContainer):
            yield from self.iter_windows(node.get_container())
            return
        if isinstance(node, FakeWindow):
            yield node
            return
        if isinstance(node, (FakeHSplit, FakeVSplit)):
            for child in node.children:
                yield from self.iter_windows(child)

    def find_window_containing(self, text: str):
        for window in self.iter_windows():
            if text in flatten_fragments(self.render_window_fragments(window)):
                return window
        raise AssertionError(f"No window contains {text!r}")

    def render_window_fragments(self, window):
        content = window.content
        if isinstance(content, FakeFormattedTextControl):
            return content.fragments()
        if isinstance(content, FakeBufferControl):
            return [("", content.buffer.text.ljust(window_width(window)))]
        if window.char:
            return [("", window.char)]
        return [("", "")]

    def render_input_line(self) -> str:
        parts = []
        for window in self.input_row.children:
            parts.append(flatten_fragments(self.render_window_fragments(window)))
        return "".join(parts)

    def tree_lines(self) -> list[str]:
        return [flatten_fragments(line) for line in split_fragment_lines(self.render_window_fragments(self.tree_window))]

    def tree_fragment_lines(self) -> list[list[tuple[str, str]]]:
        return split_fragment_lines(self.render_window_fragments(self.tree_window))

    def action_lines(self) -> list[str]:
        return [flatten_fragments(line) for line in split_fragment_lines(self.render_window_fragments(self.actions_window))]

    def action_fragment_lines(self) -> list[list[tuple[str, str]]]:
        return split_fragment_lines(self.render_window_fragments(self.actions_window))

    def help_text(self) -> str:
        return flatten_fragments(self.render_window_fragments(self.help_window))

    def screen_lines(self) -> list[str]:
        return render_node_lines(self.app.layout.container, self.render_window_fragments)

    def screen_width(self) -> int:
        return max((len(line) for line in self.screen_lines()), default=0)

    def selected_tree_line_index(self) -> int:
        marker = MODULE.THEMES["rounded"].cursor_marker
        for index, line in enumerate(self.tree_lines()):
            if marker in line:
                return index
        raise AssertionError("No selected tree line found.")

    def selected_action_line_index(self) -> int:
        marker = MODULE.THEMES["rounded"].cursor_marker
        for index, line in enumerate(self.action_lines()):
            if marker in line:
                return index
        raise AssertionError("No selected action line found.")


def make_sample_remotes() -> list[MODULE.RemoteSelection]:
    return [
        MODULE.RemoteSelection(
            name="origin",
            fetch=MODULE.make_url_selection("fetch", "https://github.com/example/origin"),
            push=MODULE.make_url_selection("push", "https://github.com/example/origin"),
            push_is_explicit=False,
        ),
        MODULE.RemoteSelection(
            name="empty",
            fetch=MODULE.make_url_selection("fetch", "https://luckydonald@github.com/example/empty"),
            push=MODULE.make_url_selection("push", "https://luckydonald@github.com/example/empty"),
            push_is_explicit=False,
        ),
        MODULE.RemoteSelection(
            name="template",
            fetch=MODULE.make_url_selection("fetch", "../template"),
            push=MODULE.make_url_selection("push", "../template"),
            push_is_explicit=False,
        ),
        MODULE.RemoteSelection(
            name="clock",
            fetch=MODULE.make_url_selection("fetch", "https://luckydonald@github.com/example/clock.git"),
            push=MODULE.make_url_selection("push", "https://luckydonald@github.com/example/clock.git"),
            push_is_explicit=False,
        ),
    ]


def make_init_example_remotes() -> list[MODULE.RemoteSelection]:
    return [
        MODULE.RemoteSelection(
            name="origin",
            fetch=MODULE.make_url_selection("fetch", "https://github.com/luckydonald/base"),
            push=MODULE.make_url_selection("push", "https://github.com/luckydonald/base.git"),
            push_is_explicit=False,
        ),
        MODULE.RemoteSelection(
            name="empty",
            fetch=MODULE.make_url_selection("fetch", "https://someone@github.com/EmptyAAS/empty"),
            push=MODULE.make_url_selection("push", "https://luckydonald@github.com/EmptyAAS/empty"),
            push_is_explicit=False,
        ),
        MODULE.RemoteSelection(
            name="template",
            fetch=MODULE.make_url_selection("fetch", "../hoass_template"),
            push=MODULE.make_url_selection("push", "https://github.com/luckydonald/hoass_plugin-template.git"),
            push_is_explicit=False,
        ),
        MODULE.RemoteSelection(
            name="clock",
            fetch=MODULE.make_url_selection(
                "fetch",
                "https://luckydonald@github.com/luckydonald/hoass_calendar-alarm-clock.git",
            ),
            push=MODULE.make_url_selection(
                "push",
                "https://luckydonald@github.com/luckydonald/hoass_calendar-alarm-clock.git",
            ),
            push_is_explicit=False,
        ),
    ]


class TuiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_modules = FakePromptToolkitModules()
        self.fake_modules.install()
        self.addCleanup(self.fake_modules.uninstall)
        self.set_terminal_size(120, 40)

    def build_ui(
        self,
        *,
        username: str = "luckydonald",
        theme: str = "rounded",
        remotes: list[MODULE.RemoteSelection] | None = None,
    ) -> FakeTuiHarness:
        app = MODULE.run_tui(remotes or make_sample_remotes(), theme=MODULE.THEMES[theme], username=username)
        return FakeTuiHarness(app)

    def set_terminal_size(self, columns: int, lines: int) -> None:
        original = MODULE.shutil.get_terminal_size
        MODULE.shutil.get_terminal_size = lambda fallback=(80, 24): os.terminal_size((columns, lines))
        self.addCleanup(setattr, MODULE.shutil, "get_terminal_size", original)

    def set_terminal_width(self, columns: int) -> None:
        self.set_terminal_size(columns, 40)

    def set_monotonic_time(self, value_ref: dict[str, float]) -> None:
        original = MODULE.time.monotonic
        MODULE.time.monotonic = lambda: value_ref["value"]
        self.addCleanup(setattr, MODULE.time, "monotonic", original)
