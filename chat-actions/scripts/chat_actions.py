import argparse
import json
import sys
from html import escape
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4


ASSETS = Path(__file__).resolve().parents[1] / "assets"
DEFAULT_DIRECTORY = Path("/Users/joel/joel/storage-for-ai/actions")
STATE_FILENAME = ".chat-actions.json"


def command_directory(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("请输入命令文件地址。")
    directory = Path(value.strip()).expanduser()
    if not directory.is_absolute():
        raise ValueError("请输入命令目录的绝对路径。")
    return directory


def read_catalog(directory):
    catalog = []
    for path in sorted(directory.iterdir(), key=lambda path: (path.name.casefold(), path.name)):
        if path.suffix.lower() != ".json" or not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict) or not isinstance(data.get("commands"), list):
                raise ValueError("需要包含 commands 数组。")
            variables = data.get("variables", {})
            if not isinstance(variables, dict) or not all(isinstance(v, dict) for v in variables.values()):
                raise ValueError("variables 必须是参数对象。")
            catalog.append((path.name, variables, data["commands"], ""))
        except (OSError, UnicodeError, ValueError) as error:
            catalog.append((path.name, {}, [], str(error)))
    return catalog


def render_field(name, field):
    attributes = f'data-variable="{escape(name)}"'
    kind = field.get("type")
    initial = field.get("default", 0 if kind == "counter" else "")
    label = escape(str(field.get("label") or name))
    if kind == "select" and isinstance(field.get("options"), list):
        options = ['<option value="">请选择</option>']
        for option in field["options"]:
            value = escape(str(option))
            selected = " selected" if option == initial else ""
            options.append(f'<option value="{value}"{selected}>{value}</option>')
        control = f'<select class="form-select" {attributes}>{"".join(options)}</select>'
    else:
        input_type = 'type="text"' if kind != "counter" else f'type="number" step="{escape(str(field.get("step", 1)))}"'
        control = f'<input class="form-control" {input_type} {attributes} value="{escape(str(initial))}">'
    return f'<label class="form-label"><span>{label}</span>{control}</label>'


def render_command(command):
    if not isinstance(command, dict) or not isinstance(command.get("template"), str):
        return '<li class="command"><p role="alert">此条命令缺少有效的 template。</p></li>'
    label = escape(str(command.get("label") or command.get("id") or "未命名命令"))
    template = escape(command["template"])
    required = command.get("requires", [])
    required_json = escape(json.dumps(required if isinstance(required, list) else []))
    actions = command.get("actions", [])
    buttons = []
    if isinstance(actions, list) and "copy" in actions:
        buttons.append(f'<button type="button" class="btn" data-action="copy" aria-label="复制 {label}">复制</button>')
    if isinstance(actions, list) and "run" in actions:
        buttons.append(f'<button type="button" class="btn btn-primary" data-action="run" aria-label="运行 {label}">运行</button>')
    return f'''<li class="command" data-command data-template="{template}" data-requires="{required_json}">
      <div class="command-text"><h3>{label}</h3><p data-preview>{template}</p></div>
      <div class="command-actions">{" ".join(buttons)}</div>
      <p class="text-small" data-status role="status"></p>
      <label class="form-label" data-manual hidden>手动复制<textarea class="form-control" rows="2" readonly></textarea></label>
    </li>'''


def render_catalog(directory, catalog, root):
    tabs, panels = [], []
    for index, (name, variables, commands, error) in enumerate(catalog):
        tab, panel = f"{root}-tab-{index}", f"{root}-panel-{index}"
        selected = "true" if index == 0 else "false"
        active = " active" if index == 0 else ""
        hidden = " hidden" if index else ""
        tabs.append(f'''<button class="nav-link{active}" type="button" role="tab" id="{tab}"
          aria-controls="{panel}" aria-selected="{selected}">{escape(name)}</button>''')
        if error:
            body = f'<p class="text-destructive" role="alert">读取失败。{escape(error)}</p>'
        elif not commands:
            body = '<p class="text-muted">此文件没有命令。</p>'
        else:
            fields = "\n".join(render_field(name, field) for name, field in variables.items())
            fieldset = f'<fieldset class="variables"><legend>命令参数</legend>{fields}</fieldset>' if fields else ""
            rows = "\n".join(render_command(command) for command in commands)
            body = f'{fieldset}<ul class="commands">{rows}</ul>'
        panels.append(f'<section id="{panel}" role="tabpanel" aria-labelledby="{tab}"{hidden}>{body}</section>')
    content = "\n".join(panels) or '<p class="text-muted">目录中没有 JSON 文件。</p>'
    tablist = f'<div class="nav nav-pills" role="tablist" aria-label="命令文件">{" ".join(tabs)}</div>' if tabs else ""
    return f'''<header><h2>命令列表</h2><p class="text-small text-muted">{escape(str(directory))}</p></header>
    {tablist}
    {content}'''


def render_settings(directory, root):
    field = f"{root}-directory"
    return f'''<header><h2>命令设置</h2></header>
    <div data-settings>
      <label class="form-label" for="{field}">命令文件地址</label>
      <div class="settings-controls">
        <input id="{field}" class="form-control" name="directory" type="text" value="{escape(str(directory))}" required spellcheck="false">
        <button type="button" class="btn btn-primary">保存</button>
      </div>
      <p class="text-small" data-status role="status"></p>
      <label class="form-label" data-manual hidden>复制后发送到当前聊天<textarea class="form-control" rows="3" readonly></textarea></label>
    </div>'''


def atomic_write(path, content):
    with NamedTemporaryFile(mode="w", dir=path.parent, encoding="utf-8", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("settings", "list", "save"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--text", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    state = output / STATE_FILENAME
    try:
        if args.mode == "save":
            request = json.load(sys.stdin)
            if not isinstance(request, dict):
                raise ValueError("设置必须使用 JSON 对象。")
            directory = command_directory(request.get("directory"))
        elif state.exists():
            directory = command_directory(json.loads(state.read_text(encoding="utf-8"))["directory"])
        else:
            directory = DEFAULT_DIRECTORY

        root = f"chat-actions-{uuid4().hex}"
        view = "settings" if args.mode == "settings" else "list"
        if view == "settings":
            markup = render_settings(directory, root)
        else:
            catalog = read_catalog(directory)
            if args.mode == "list" and args.text:
                print(directory)
                for name, _, commands, error in catalog:
                    print(f"\n{name}")
                    if error:
                        print(f"读取失败。{error}")
                    for command in commands:
                        if isinstance(command, dict):
                            print(f"- {command.get('label') or command.get('id')}  {command.get('template', '')}")
                return
            markup = render_catalog(directory, catalog, root)

        css = (ASSETS / "card.css").read_text(encoding="utf-8").replace("__ROOT__", root)
        script = (ASSETS / "card.js").read_text(encoding="utf-8").replace("__ROOT__", root)
        fragment = f'<div id="{root}" lang="zh-CN">{markup}</div>\n<style>\n{css}</style>\n<script>\n{script}</script>\n'
        if len(fragment.encode("utf-8")) > 1_000_000:
            raise ValueError("命令列表超过聊天视图容量。")
        output.mkdir(parents=True, exist_ok=True)
        path = output / f"{root}-{view}.html"
        atomic_write(path, fragment)
        if args.mode == "save":
            atomic_write(state, json.dumps({"directory": str(directory)}, ensure_ascii=False) + "\n")
        print(path)
    except (OSError, UnicodeError, ValueError, KeyError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
