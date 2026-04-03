from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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


class FakeApplication:
    def __init__(self, *, layout, key_bindings, style, full_screen, mouse_support) -> None:
        self.layout = layout
        self.key_bindings = key_bindings
        self.style = style
        self.full_screen = full_screen
        self.mouse_support = mouse_support
        self.exit_result = None
        FAKE_RUNTIME.current_app = self

    def exit(self, result=None) -> None:
        self.exit_result = result

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


class FakeTuiHarness:
    def __init__(self, app) -> None:
        self.app = app
        self.edit_container = self.app.layout.container.get_container()
        self.input_container = self.edit_container.children[1]
        self.input_row = self.input_container.children[1]
        self.username_window = self.input_row.children[1]
        self.tree_window = self.edit_container.children[4]
        self.actions_window = self.edit_container.children[6]
        self.status_window = self.edit_container.children[8]
        self.help_window = self.edit_container.children[9]

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


class TuiTddTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_modules = FakePromptToolkitModules()
        self.fake_modules.install()
        self.addCleanup(self.fake_modules.uninstall)

    def build_ui(self, *, username: str = "luckydonald", theme: str = "rounded") -> FakeTuiHarness:
        app = MODULE.run_tui(make_sample_remotes(), theme=MODULE.THEMES[theme], username=username)
        return FakeTuiHarness(app)

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
        ui.press("down", times=40)
        self.assertIs(ui.app.layout.current_window, ui.actions_window)
        self.assertEqual(ui.selected_action_line_index(), 0)

    def test_tdd_check_all_up_moves_back_to_last_multi_select_item(self) -> None:
        ui = self.build_ui()
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
                "    ▶ Preview changes",
                "    ✕ Cancel",
            ],
        )

    def test_tdd_help_footer_hides_action_shortcuts_in_text_field_and_uses_new_format(self) -> None:
        ui = self.build_ui()
        help_text = ui.help_text()
        self.assertIn("Tab)  focus", help_text)
        self.assertIn("⬆︎|⬇︎)  move", help_text)
        self.assertIn("←|→)  move cursor", help_text)
        self.assertIn("Enter) next element/submit", help_text)
        self.assertNotIn("𝚊)", help_text)
        self.assertNotIn("𝚗)", help_text)
        self.assertNotIn("𝚚|␛)", help_text)

    def test_tdd_help_footer_shows_arrow_keys_escape_symbol_and_monospace_hotkeys_in_multi_select(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        help_text = ui.help_text()
        self.assertIn("Tab)  focus", help_text)
        self.assertIn("⬆︎|⬇︎)  move", help_text)
        self.assertIn("Enter)  next element/submit", help_text)
        self.assertIn("𝚊)  check all", help_text)
        self.assertIn("𝚗)  check none", help_text)
        self.assertIn("𝚚|␛)  cancel", help_text)

    def test_tdd_enter_in_name_field_moves_focus_to_multi_select(self) -> None:
        ui = self.build_ui()
        ui.press("enter")
        self.assertIs(ui.app.layout.current_window, ui.tree_window)

    def test_tdd_input_border_focus_uses_highlight_color(self) -> None:
        ui = self.build_ui()
        self.assertEqual(ui.app.style.style_rules["input-border-active"], "ansimagenta bold")

    def test_tdd_focused_input_uses_template_cursor_glyph(self) -> None:
        ui = self.build_ui(theme="boxy")
        self.assertIn("▎", ui.render_input_line())

    def test_tdd_cursor_glyph_uses_highlight_color(self) -> None:
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
        submit_window = ui.find_window_containing("Submit")
        ui.press("tab")
        ui.press("tab")
        ui.press("tab")
        self.assertIs(ui.app.layout.current_window, submit_window)

    def test_tdd_submit_button_is_reachable_via_down_logic(self) -> None:
        ui = self.build_ui()
        ui.press("down")
        ui.press("down", times=40)
        submit_window = ui.find_window_containing("Submit")
        self.assertIs(ui.app.layout.current_window, submit_window)

    def test_tdd_submit_button_focus_is_fully_highlighted(self) -> None:
        ui = self.build_ui()
        submit_window = ui.find_window_containing("Submit")
        ui.press("tab")
        ui.press("tab")
        ui.press("tab")
        submit_fragments = ui.render_window_fragments(submit_window)
        non_space_styles = {style for style, text in submit_fragments if text.strip()}
        self.assertEqual(non_space_styles, {"class:selected-marker"})

    def test_tdd_click_feedback_uses_mouse_support_and_025s_flash(self) -> None:
        ui = self.build_ui()
        self.assertTrue(ui.app.mouse_support)
        self.assertEqual(getattr(MODULE, "FLASH_FEEDBACK_SECONDS"), 0.25)


if __name__ == "__main__":
    unittest.main()
