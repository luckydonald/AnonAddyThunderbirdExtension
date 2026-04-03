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
        self.output = FakeOutput()

    def clear(self) -> None:
        self.clear_count += 1


class FakeOutput:
    def __init__(self) -> None:
        self.operations: list[tuple] = []

    def cursor_goto(self, row: int = 0, column: int = 0) -> None:
        self.operations.append(("cursor_goto", row, column))

    def cursor_up(self, amount: int) -> None:
        self.operations.append(("cursor_up", amount))

    def cursor_down(self, amount: int) -> None:
        self.operations.append(("cursor_down", amount))

    def cursor_forward(self, amount: int) -> None:
        self.operations.append(("cursor_forward", amount))

    def cursor_backward(self, amount: int) -> None:
        self.operations.append(("cursor_backward", amount))

    def erase_end_of_line(self) -> None:
        self.operations.append(("erase_end_of_line",))

    def write(self, text: str) -> None:
        self.operations.append(("write", text))

    def write_raw(self, text: str) -> None:
        self.operations.append(("write_raw", text))

    def flush(self) -> None:
        self.operations.append(("flush",))


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


class FakeTerminalBuffer:
    def __init__(self, lines: list[str], *, width: int, height: int) -> None:
        padded = [line.ljust(width)[:width] for line in lines[:height]]
        if len(padded) < height:
            padded.extend([" " * width for _ in range(height - len(padded))])
        self.lines = [list(line) for line in padded]
        self.width = width
        self.height = height
        self.row = 0
        self.column = 0

    def apply(self, operations: list[tuple]) -> None:
        for operation in operations:
            name = operation[0]
            if name == "cursor_goto":
                self.row = max(0, min(self.height - 1, max(1, operation[1]) - 1))
                self.column = max(0, min(self.width - 1, max(1, operation[2]) - 1))
                continue
            if name == "cursor_up":
                self.row = max(0, self.row - operation[1])
                continue
            if name == "cursor_down":
                self.row = min(self.height - 1, self.row + operation[1])
                continue
            if name == "cursor_forward":
                self.column = min(self.width - 1, self.column + operation[1])
                continue
            if name == "cursor_backward":
                self.column = max(0, self.column - operation[1])
                continue
            if name == "erase_end_of_line":
                for index in range(self.column, self.width):
                    self.lines[self.row][index] = " "
                continue
            if name in {"write", "write_raw"}:
                self._write_text(operation[1])
                continue

    def _write_text(self, text: str) -> None:
        for character in text:
            if character == "\r":
                self.column = 0
                continue
            if character == "\n":
                self.row = min(self.height - 1, self.row + 1)
                continue
            if 0 <= self.row < self.height and 0 <= self.column < self.width:
                self.lines[self.row][self.column] = character
            self.column = min(self.width - 1, self.column + 1)

    def rendered_lines(self, count: int) -> list[str]:
        return ["".join(line) for line in self.lines[:count]]


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


class TuiTddTests(unittest.TestCase):
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

    def build_terminal_buffer(self, ui: FakeTuiHarness) -> FakeTerminalBuffer:
        lines = ui.screen_lines()
        return FakeTerminalBuffer(
            lines,
            width=max(MODULE.shutil.get_terminal_size(fallback=(80, 24)).columns, 1),
            height=MODULE.shutil.get_terminal_size(fallback=(80, 24)).lines,
        )

    def merged_screen_after_keys(self, ui: FakeTuiHarness, keys: list[str]) -> list[str]:
        buffer = self.build_terminal_buffer(ui)
        for key in keys:
            ui.app.renderer.output.operations.clear()
            ui.press(key)
            buffer.apply(ui.app.renderer.output.operations)
        expected = ui.screen_lines()
        return buffer.rendered_lines(len(expected))

    def padded_screen_lines(self, ui: FakeTuiHarness) -> list[str]:
        width = max(MODULE.shutil.get_terminal_size(fallback=(80, 24)).columns, 1)
        return [line.ljust(width)[:width] for line in ui.screen_lines()]

    def test_tdd_starts_with_name_field_focused_and_cursor_at_end(self) -> None:
        ui = self.build_ui()
        self.assertIs(ui.app.layout.current_window, ui.username_window)
        self.assertEqual(ui.username_window.content.buffer.cursor_position, len("luckydonald"))

    def test_tdd_name_field_down_arrow_moves_focus_to_multi_select(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        self.assertIs(ui.app.layout.current_window, ui.tree_window)

    def test_tdd_multi_select_up_from_top_returns_to_name_field(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        ui.press("up")
        self.assertIs(ui.app.layout.current_window, ui.username_window)

    def test_tdd_multi_select_up_moves_to_previous_item(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        ui.press("down", times=2)
        self.assertEqual(ui.selected_tree_line_index(), 2)
        ui.press("up")
        self.assertEqual(ui.selected_tree_line_index(), 1)

    def test_tdd_multi_select_down_from_last_item_moves_to_check_all(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        while ui.app.layout.current_window is ui.tree_window:
            ui.press("down")
        self.assertIs(ui.app.layout.current_window, ui.actions_window)
        self.assertEqual(ui.selected_action_line_index(), 0)

    def test_tdd_check_all_up_moves_back_to_last_multi_select_item(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        while ui.app.layout.current_window is ui.tree_window:
            ui.press("down")
        ui.press("up")
        self.assertIs(ui.app.layout.current_window, ui.tree_window)

    def test_tdd_edit_screen_separates_scrollable_body_from_fixed_footer(self) -> None:
        ui = self.build_ui()
        self.assertEqual(
            len(ui.edit_container.children),
            2,
            "Expected a scrollable body and a fixed gray footer, not one flat edit stack.",
        )

    def test_tdd_input_line_matches_template_width_without_extra_trailing_space(self) -> None:
        ui = self.build_ui(theme="boxy")
        ui.press("down")
        self.assertEqual(
            ui.render_input_line(),
            "  │ ✎ │ luckydonald                              │",
        )

    def test_tdd_selected_indicator_uses_highlight_color(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        first_tree_line = ui.tree_fragment_lines()[0]
        marker_fragment = next(fragment for fragment in first_tree_line if MODULE.THEMES["rounded"].cursor_marker in fragment[1])
        self.assertEqual(marker_fragment[0], "class:selected-marker")
        self.assertEqual(ui.app.style.style_rules["selected-marker"], "ansimagenta bold")

    def test_tdd_remote_name_uses_highlight_color(self) -> None:
        ui = self.build_ui()
        self.assertEqual(ui.app.style.style_rules["remote-name"], "ansimagenta bold")

    def test_tdd_active_checkbox_icons_use_highlight_color(self) -> None:
        ui = self.build_ui()
        self.assertEqual(ui.app.style.style_rules["icon-active"], "ansimagenta bold")

    def test_tdd_partial_and_disabled_icons_are_not_colored_when_unfocused(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        lines = ui.tree_fragment_lines()
        partial_line = next(line for line in lines if "empty" in flatten_fragments(line))
        disabled_line = next(line for line in lines if "template" in flatten_fragments(line))
        partial_icon = next(fragment for fragment in partial_line if "◑" in fragment[1])
        disabled_icon = next(fragment for fragment in disabled_line if "◠" in fragment[1])
        self.assertEqual(partial_icon[0], "")
        self.assertEqual(disabled_icon[0], "")

    def test_tdd_parent_icons_are_not_colored_unless_directly_focused(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        ui.press("down")
        origin_line = next(line for line in ui.tree_fragment_lines() if "origin" in flatten_fragments(line))
        origin_icon = next(fragment for fragment in origin_line if "◉" in fragment[1])
        self.assertEqual(origin_icon[0], "")

    def test_tdd_action_icons_are_not_colored_when_actions_are_unfocused(self) -> None:
        ui = self.build_ui()
        first_action_line = ui.action_fragment_lines()[0]
        action_icon = next(fragment for fragment in first_action_line if MODULE.THEMES["rounded"].select_all_icon in fragment[1])
        self.assertEqual(action_icon[0], "")

    def test_tdd_check_all_and_check_none_have_no_blank_line_between_them(self) -> None:
        ui = self.build_ui()
        self.assertEqual(
            ui.action_lines(),
            [
                "    ◉ Check all",
                "    ◎ Check none",
            ],
        )

    def test_tdd_help_footer_hides_action_shortcuts_in_text_field_and_uses_new_format(self) -> None:
        ui = self.build_ui()
        help_text = ui.help_text()
        self.assertIn("⇥⟯  focus", help_text)
        self.assertIn("↑|↓⟯  move", help_text)
        self.assertIn("←|→⟯  move cursor", help_text)
        self.assertIn("⏎⟯  next element/submit", help_text)
        self.assertIn("𝚛⟯  refresh", help_text)
        self.assertNotIn("𝚊⟯", help_text)
        self.assertNotIn("𝚗⟯", help_text)
        self.assertNotIn("𝚚|␛⟯", help_text)

    def test_tdd_help_footer_shows_arrow_keys_escape_symbol_and_monospace_hotkeys_in_multi_select(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        help_text = ui.help_text()
        self.assertIn("⇥⟯  focus", help_text)
        self.assertIn("↑|↓⟯  move", help_text)
        self.assertIn("⏎⟯  next element/submit", help_text)
        self.assertIn("𝚊⟯  check all", help_text)
        self.assertIn("𝚗⟯  check none", help_text)
        self.assertIn("𝚛⟯  refresh", help_text)
        self.assertIn("𝚚|␛⟯  cancel", help_text)

    def test_tdd_refresh_hotkey_invalidates_the_app(self) -> None:
        ui = self.build_ui()
        self.assertEqual(ui.app.invalidate_count, 0)
        ui.press("r")
        self.assertEqual(ui.app.invalidate_count, 1)

    def test_tdd_refresh_hotkey_clears_the_screen_and_keeps_current_state(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        ui.press("down", times=5)
        selected_index = ui.selected_tree_line_index()
        prior_clear_count = ui.app.renderer.clear_count
        prior_invalidate_count = ui.app.invalidate_count
        ui.press("r")
        self.assertEqual(ui.app.renderer.clear_count, prior_clear_count + 1)
        self.assertEqual(ui.app.invalidate_count, prior_invalidate_count + 1)
        self.assertIs(ui.app.layout.current_window, ui.tree_window)
        self.assertEqual(ui.selected_tree_line_index(), selected_index)

    def test_tdd_navigation_does_not_full_clear_on_every_input(self) -> None:
        ui = self.build_ui()
        self.assertEqual(ui.app.renderer.clear_count, 0)
        ui.press("down")
        ui.press("down")
        ui.press("down")
        while ui.app.layout.current_window is ui.tree_window:
            ui.press("down")
        ui.press("down")
        self.assertEqual(ui.app.renderer.clear_count, 0)
        self.assertGreater(ui.app.invalidate_count, 0)

    def test_tdd_second_level_active_icon_keeps_active_shape_when_suffix_turns_off(self) -> None:
        remotes = [
            MODULE.RemoteSelection(
                name="origin",
                fetch=MODULE.make_url_selection("fetch", "https://github.com/example/origin"),
                push=MODULE.make_url_selection("push", "https://github.com/example/origin"),
                push_is_explicit=False,
            )
        ]
        remotes[0].fetch.change_username = False
        remotes[0].fetch.add_git_suffix = False
        remotes[0].push.change_username = False
        remotes[0].push.add_git_suffix = False

        ui = self.build_ui(remotes=remotes)
        ui.press("down")
        ui.press("down", times=3)

        self.assertIn("○ push", ui.tree_lines()[3])
        self.assertIn("○ Add .git suffix", ui.tree_lines()[4])

        ui.press("down")
        ui.press("space")
        self.assertIn("◒ push", ui.tree_lines()[3])
        self.assertIn("● Add .git suffix", ui.tree_lines()[4])

        ui.press("up")
        ui.press("space")
        self.assertIn("● push", ui.tree_lines()[3])
        self.assertIn("● Add .git suffix", ui.tree_lines()[4])

        ui.press("down")
        ui.press("space")
        self.assertTrue(
            any(icon in ui.tree_lines()[3] for icon in ("◓ push", "● push")),
            ui.tree_lines()[3],
        )
        self.assertIn("○ Add .git suffix", ui.tree_lines()[4])

    def test_tdd_input_border_extends_by_two_characters(self) -> None:
        ui = self.build_ui(theme="rounded")
        self.assertEqual(
            flatten_fragments(ui.render_window_fragments(ui.input_container.children[0])),
            "  ╭───┬──────────────────────────────────────────╮",
        )
        self.assertEqual(
            flatten_fragments(ui.render_window_fragments(ui.input_container.children[2])),
            "  ╰━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯",
        )

    def test_tdd_input_box_grows_to_terminal_width_minus_two(self) -> None:
        self.set_terminal_width(72)
        ui = self.build_ui(username="luckydonald-with-a-very-long-name-that-should-grow")
        top_line = flatten_fragments(ui.render_window_fragments(ui.input_container.children[0]))
        mid_line = ui.render_input_line()
        bottom_line = flatten_fragments(ui.render_window_fragments(ui.input_container.children[2]))
        self.assertEqual(len(top_line), 70)
        self.assertEqual(len(mid_line), 70)
        self.assertEqual(len(bottom_line), 70)

    def test_tdd_long_input_scrolls_with_leading_ellipsis_and_keeps_cursor_space(self) -> None:
        self.set_terminal_width(72)
        self.set_monotonic_time({"value": 0.10})
        ui = self.build_ui(username="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdef")
        line = ui.render_input_line()
        self.assertIn("…", line)
        self.assertIn("▁ ", line)

    def test_tdd_long_input_scrolls_with_both_ellipses_when_cursor_is_in_the_middle(self) -> None:
        self.set_terminal_width(72)
        ui = self.build_ui(username="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdef")
        ui.press("left", times=20)
        line = ui.render_input_line()
        self.assertGreaterEqual(line.count("…"), 2)

    def test_tdd_cursor_blinks_once_per_second_instead_of_staying_static(self) -> None:
        clock = {"value": 0.10}
        self.set_monotonic_time(clock)
        ui = self.build_ui(theme="boxy")

        blink_on_line = ui.render_input_line()
        blink_on_fragments = ui.render_window_fragments(ui.username_window)

        clock["value"] = 0.75
        blink_off_line = ui.render_input_line()
        blink_off_fragments = ui.render_window_fragments(ui.username_window)

        self.assertNotEqual(blink_on_line, blink_off_line)
        self.assertIn("▁", blink_on_line)
        self.assertNotIn("▁", blink_off_line)
        self.assertTrue(
            any(style == "class:selected-marker" for style, text in blink_off_fragments if text),
            blink_off_fragments,
        )

    def test_tdd_enter_in_name_field_moves_focus_to_multi_select(self) -> None:
        ui = self.build_ui()
        ui.press("enter")
        self.assertIs(ui.app.layout.current_window, ui.tree_window)

    def test_tdd_input_border_focus_uses_highlight_color(self) -> None:
        ui = self.build_ui()
        self.assertEqual(ui.app.style.style_rules["input-border-active"], "ansimagenta bold")

    def test_tdd_focused_input_uses_template_cursor_glyph(self) -> None:
        self.set_monotonic_time({"value": 0.10})
        ui = self.build_ui(theme="boxy")
        self.assertIn("▁", ui.render_input_line())

    def test_tdd_cursor_glyph_uses_highlight_color(self) -> None:
        self.set_monotonic_time({"value": 0.10})
        ui = self.build_ui(theme="boxy")
        input_fragments = ui.render_window_fragments(ui.username_window)
        cursor_fragments = [fragment for fragment in input_fragments if "▎" in fragment[1] or "▁" in fragment[1]]
        self.assertTrue(cursor_fragments, "Expected a visible cursor glyph fragment.")
        if cursor_fragments:
            self.assertEqual(cursor_fragments[0][0], "class:selected-marker")

    def test_tdd_tab_and_shift_tab_focus_switches_still_work(self) -> None:
        ui = self.build_ui()
        ui.press("tab")
        self.assertIs(ui.app.layout.current_window, ui.tree_window)
        ui.press("tab")
        self.assertIs(ui.app.layout.current_window, ui.actions_window)
        ui.press("s-tab")
        self.assertIs(ui.app.layout.current_window, ui.tree_window)

    def test_tdd_submit_button_exists_as_fourth_focus_group(self) -> None:
        ui = self.build_ui()
        ui.press("tab")
        ui.press("tab")
        ui.press("tab")
        self.assertIs(ui.app.layout.current_window, ui.submit_window)

    def test_tdd_submit_button_is_reachable_via_down_logic(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        while ui.app.layout.current_window is ui.tree_window:
            ui.press("down")
        ui.press("down")
        ui.press("down")
        self.assertIs(ui.app.layout.current_window, ui.submit_window)

    def test_tdd_submit_button_focus_is_fully_highlighted(self) -> None:
        ui = self.build_ui()
        ui.press("tab")
        ui.press("tab")
        ui.press("tab")
        submit_fragments = ui.render_window_fragments(ui.submit_window)
        non_space_styles = {style for style, text in submit_fragments if text.strip()}
        self.assertEqual(non_space_styles, {"class:selected-marker"})

    def test_tdd_click_feedback_uses_mouse_support_and_025s_flash(self) -> None:
        ui = self.build_ui()
        self.assertTrue(ui.app.mouse_support)
        self.assertEqual(getattr(MODULE, "FLASH_FEEDBACK_SECONDS"), 0.25)

    def test_tdd_ctrl_c_cancels_like_q(self) -> None:
        ui = self.build_ui()
        ui.press("c-c")
        self.assertIsNone(ui.app.exit_result)

    def test_tdd_local_redraw_rewrites_changed_rows_in_place(self) -> None:
        ui = self.build_ui()
        ui.app.renderer.output.operations.clear()
        ui.press("down")
        self.assertEqual(
            ui.app.renderer.output.operations,
            [
                ("cursor_goto", 1, 0),
                ("erase_end_of_line",),
                ("write", "  ╭───┬──────────────────────────────────────────╮"),
                ("cursor_goto", 2, 0),
                ("erase_end_of_line",),
                ("write", "  │ ✎ │ luckydonald                              │"),
                ("cursor_goto", 3, 0),
                ("erase_end_of_line",),
                ("write", "  ╰━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"),
                ("cursor_goto", 6, 0),
                ("erase_end_of_line",),
                ("write", "⋑    ◉ origin"),
                ("flush",),
            ],
        )

    def test_tdd_blink_redraw_writes_text_row_without_extra_column_shift(self) -> None:
        clock = {"value": 0.75}
        self.set_monotonic_time(clock)
        ui = self.build_ui(theme="boxy")
        ui.app.renderer.output.operations.clear()
        ui.press("left", times=4)
        self.assertIn(
            ("write", "  │ ✎ │ luckydonald                              │"),
            ui.app.renderer.output.operations,
        )

    def test_tdd_scroll_wheel_moves_like_up_and_down(self) -> None:
        ui = self.build_ui()
        ui.press("scrolldown")
        self.assertIs(ui.app.layout.current_window, ui.tree_window)
        ui.press("scrolldown")
        self.assertEqual(ui.selected_tree_line_index(), 1)
        ui.press("scrollup")
        self.assertEqual(ui.selected_tree_line_index(), 0)
        ui.press("scrollup")
        self.assertIs(ui.app.layout.current_window, ui.username_window)

    def test_tdd_checked_suffix_icon_is_not_colored_when_unfocused(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        suffix_line = next(line for line in ui.tree_fragment_lines() if "Add .git suffix" in flatten_fragments(line))
        suffix_icon = next(fragment for fragment in suffix_line if "●" in fragment[1])
        self.assertEqual(suffix_icon[0], "")

    def test_tdd_tree_scrolls_to_keep_selected_row_centered_when_terminal_is_short(self) -> None:
        self.set_terminal_size(80, 20)
        ui = self.build_ui()
        ui.press("down", times=7)
        self.assertEqual(len(ui.tree_lines()), 7)
        self.assertIn(ui.selected_tree_line_index(), range(2, 5))
        self.assertTrue(any("empty" in line for line in ui.tree_lines()))

    def test_tdd_round4_single_down_and_up_preserve_merged_screen(self) -> None:
        scenarios = [
            ("sample", make_sample_remotes()),
            ("init", make_init_example_remotes()),
        ]
        for height in (20, 28, 40):
            for label, remotes in scenarios:
                with self.subTest(height=height, scenario=label):
                    self.set_terminal_size(120, height)
                    ui = self.build_ui(remotes=remotes)
                    expected = self.padded_screen_lines(ui)
                    merged = self.merged_screen_after_keys(ui, ["down", "up"])
                    self.assertEqual(merged, expected)

    def test_tdd_round4_two_down_and_up_cycles_preserve_merged_screen(self) -> None:
        scenarios = [
            ("sample", make_sample_remotes()),
            ("init", make_init_example_remotes()),
        ]
        for height in (20, 28, 40):
            for label, remotes in scenarios:
                with self.subTest(height=height, scenario=label):
                    self.set_terminal_size(120, height)
                    ui = self.build_ui(remotes=remotes)
                    expected = self.padded_screen_lines(ui)
                    merged = self.merged_screen_after_keys(ui, ["down", "up", "down", "up"])
                    self.assertEqual(merged, expected)

    def test_tdd_round4_full_down_and_up_path_preserve_merged_screen(self) -> None:
        scenarios = [
            ("sample", make_sample_remotes()),
            ("init", make_init_example_remotes()),
        ]
        for height in (20, 28, 40):
            for label, remotes in scenarios:
                with self.subTest(height=height, scenario=label):
                    self.set_terminal_size(120, height)
                    ui = self.build_ui(remotes=remotes)
                    selectable_tree_rows = sum(1 for line in ui.tree_lines() if line)
                    down_keys = ["down"]
                    down_keys.extend(["down"] * max(0, selectable_tree_rows - 1))
                    down_keys.extend(["down", "down"])
                    up_keys = ["up"] * len(down_keys)
                    expected = self.padded_screen_lines(ui)
                    merged = self.merged_screen_after_keys(ui, down_keys + up_keys)
                    self.assertEqual(merged, expected)

    def test_tdd_round4_single_down_matches_direct_rendered_screen(self) -> None:
        self.set_terminal_size(120, 28)
        ui = self.build_ui(remotes=make_init_example_remotes())
        merged = self.merged_screen_after_keys(ui, ["down"])
        self.assertEqual(merged, self.padded_screen_lines(ui))

    def test_tdd_round4_single_down_keeps_first_remote_on_its_own_row(self) -> None:
        self.set_terminal_size(120, 28)
        ui = self.build_ui(remotes=make_init_example_remotes())
        merged = self.merged_screen_after_keys(ui, ["down"])
        expected = self.padded_screen_lines(ui)
        self.assertEqual(merged[5:11], expected[5:11])


if __name__ == "__main__":
    unittest.main()
