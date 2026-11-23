import argparse
import json
import re
import sqlite3
import sys
from datetime import date
from functools import partial
from html import escape
from os import scandir
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import NamedTuple, Union
from uuid import uuid4

from daily_totals import read_totals, record_increment, record_reset
from group_info import render_group_html


ASSETS = Path(__file__).resolve().parents[1] / "assets"
STATE_FILENAME = ".chat-actions.json"
NUMBER_TYPES = ("number", "counter", "count")


class CommandFile(NamedTuple):
    filename: str
    name: str
    variables: dict
    commands: list
    info: Union[str, list[str]]
    error: str = ""


def command_directory(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("请输入命令目录。")
    directory = Path(value.strip()).expanduser()
    if not directory.is_absolute():
        raise ValueError("请输入命令目录的绝对路径。")
    return directory


def command_files(directory):
    return sorted(
        (path for path in directory.iterdir() if path.suffix.lower() == ".json" and path.is_file()),
        key=lambda path: (path.name.casefold(), path.name),
    )


def selected_command_file(directory, name):
    if not isinstance(name, str) or not name or "\x00" in name:
        raise ValueError("请用 #init 选择命令文件。")
    path = Path(name)
    if path.name != name or path.suffix.lower() != ".json":
        raise ValueError("请用 #init 选择命令文件。")
    path = directory / path
    if not path.is_file():
        raise ValueError(f"命令文件「{name}」不存在，请用 #init 重新选择。")
    return path


def increment_rule(command, variables):
    rule = command.get("increment")
    if rule is None:
        return None
    local = command.get("variables", {})
    if isinstance(rule, dict) and isinstance(local, dict):
        target, amount = rule.get("variable"), rule.get("by")
        if isinstance(target, str) and isinstance(amount, str) and isinstance(command.get("id"), str):
            target_field, amount_field = variables.get(target), local.get(amount)
            if (target_field and target_field.get("type") in NUMBER_TYPES
                    and isinstance(amount_field, dict) and amount_field.get("type") in NUMBER_TYPES):
                return rule
    raise ValueError("increment 需要命令 id、分组数字变量 variable 和局部数字变量 by。")


def reset_variable(command, variables):
    target = command.get("reset")
    if target is None:
        return None
    if (isinstance(target, str) and target and isinstance(command.get("id"), str)
            and command.get("increment") is None and variables.get(target, {}).get("type") in NUMBER_TYPES):
        return target
    raise ValueError("reset 需要命令 id 和分组数字变量名称，并且应单独配置。")


def read_commands(path, totals=None):
    display_name = path.stem
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or not isinstance(data.get("commands"), list):
            raise ValueError("需要包含 commands 数组。")
        name = data.get("name")
        if isinstance(name, str) and name.strip():
            display_name = name.strip()
        variables = data.get("variables", {})
        if not isinstance(variables, dict) or not all(isinstance(v, dict) for v in variables.values()):
            raise ValueError("variables 必须是参数对象。")
        info = data.get("info", [])
        if not isinstance(info, str) and not (isinstance(info, list) and all(isinstance(item, str) for item in info)):
            raise ValueError("info 必须是 HTML 字符串或文本列表。")
        totals = totals or {}
        for command in data["commands"]:
            if not isinstance(command, dict):
                continue
            target = reset_variable(command, variables)
            rule = increment_rule(command, variables)
            if rule:
                target = rule["variable"]
            if target:
                variables[target] = {**variables[target], "default": totals.get(target, "0"), "readonly": True}
        return CommandFile(path.name, display_name, variables, data["commands"], info)
    except (OSError, UnicodeError, ValueError) as error:
        return CommandFile(path.name, display_name, {}, [], [], str(error))


def initial_value(field):
    return field.get("default", 0 if field.get("type") in NUMBER_TYPES else "")


def format_group_info(template, variables):
    def replace(match):
        value = str(initial_value(variables.get(match[1], {}))).strip()
        return value or match[0]

    return re.sub(r"\{([\w.-]+)\}", replace, template)


def render_field(name, field):
    attributes = f'data-variable="{escape(name)}"'
    kind = field.get("type")
    numeric = kind in NUMBER_TYPES
    initial = initial_value(field)
    label = escape(str(field.get("label") or name))
    if kind == "select" and isinstance(field.get("options"), list):
        options = ['<option value="">请选择</option>']
        for option in field["options"]:
            value = escape(str(option))
            selected = " selected" if option == initial else ""
            options.append(f'<option value="{value}"{selected}>{value}</option>')
        control = f'<select class="form-select" {attributes}>{"".join(options)}</select>'
    else:
        input_type = f'type="number" step="{escape(str(field.get("step", 1)))}"' if numeric else 'type="text"'
        readonly = " readonly" if field.get("readonly") else ""
        control = f'<input class="form-control" {input_type} {attributes} value="{escape(str(initial))}"{readonly}>'
    return f'<label class="form-label"><span>{label}</span>{control}</label>'


def render_command(command, grouped=False):
    classes = "command" if grouped else "card command"
    if not isinstance(command, dict) or not isinstance(command.get("template"), str):
        return f'<li class="{classes}"><p role="alert">此条命令缺少有效的 template。</p></li>'
    label = escape(str(command.get("label") or command.get("id") or "未命名命令"))
    template = escape(command["template"])
    required = command.get("requires", [])
    required_json = escape(json.dumps(required if isinstance(required, list) else []))
    local_variables = command.get("variables", {})
    if not isinstance(local_variables, dict) or not all(isinstance(v, dict) for v in local_variables.values()):
        return f'<li class="{classes}"><p role="alert">命令的 variables 必须是参数对象。</p></li>'
    local_fields = "".join(render_field(name, field) for name, field in local_variables.items())
    rule = command.get("increment")
    action_attributes = ""
    if rule or command.get("reset"):
        action_attributes = f' data-command-id="{escape(command["id"])}"'
        action_attributes += f' data-increment-by="{escape(rule["by"])}"' if rule else " data-reset"
    actions = command.get("actions", [])
    buttons = []
    if isinstance(actions, list) and "copy" in actions:
        buttons.append(f'<button type="button" class="btn" data-action="copy" aria-label="复制 {label}">复制</button>')
    if isinstance(actions, list) and "run" in actions:
        run_classes = "btn" if command.get("reset") else "btn btn-primary"
        buttons.append(f'<button type="button" class="{run_classes}" data-action="run" aria-label="运行 {label}">运行</button>')
    heading = "h4" if grouped else "h3"
    return f'''<li class="{classes}" data-command data-template="{template}" data-requires="{required_json}"{action_attributes}>
      <div class="command-text"><{heading}>{label}</{heading}><p data-preview>{template}</p></div>
      <div class="command-actions">{" ".join(buttons)}</div>
      <p class="text-small" data-status role="status"></p>
      <label class="form-label" data-manual hidden>手动复制<textarea class="form-control" rows="2" readonly></textarea></label>
      {f'<div data-local-variables hidden>{local_fields}</div>' if local_fields else ''}
    </li>'''


def render_command_cards(commands):
    groups = {}
    for index, command in enumerate(commands):
        configured_name = command.get("card") if isinstance(command, dict) else None
        name = configured_name.strip() if isinstance(configured_name, str) else ""
        groups.setdefault(name or index, []).append(command)

    cards = []
    for name, entries in groups.items():
        if isinstance(name, str):
            rows = "\n".join(render_command(command, grouped=True) for command in entries)
            cards.append(f'<li class="card command-card"><h3>{escape(name)}</h3><ul class="card-commands">{rows}</ul></li>')
        else:
            cards.append(render_command(entries[0]))
    return "\n".join(cards)


def render_commands(entry):
    if entry.error:
        return f'<p class="text-destructive" role="alert">读取失败。{escape(entry.error)}</p>'
    variables, commands, info = entry.variables, entry.commands, entry.info
    details = ""
    if isinstance(info, str) and info.strip():
        html, _ = render_group_html(info, partial(format_group_info, variables=variables))
        if html.strip():
            details = f'<div class="group-info" role="group" aria-label="分组信息">{html}</div>'
    elif isinstance(info, list) and info:
        items = "".join(
            f'<li data-group-info="{escape(item)}">{escape(format_group_info(item, variables))}</li>'
            for item in info
        )
        details = f'<ul class="group-info" aria-label="分组信息">{items}</ul>'
    fields = "\n".join(render_field(name, field) for name, field in variables.items())
    parameters = ""
    if fields:
        parameters = f'''<details class="command-parameters">
          <summary>变量</summary>
          <fieldset class="variables" aria-label="变量">{fields}</fieldset>
        </details>'''
    rows = render_command_cards(commands)
    command_list = f'<ul class="commands">{rows}</ul>' if rows else '<p class="text-muted">此文件没有命令。</p>'
    return f'{details}{command_list}{parameters}'


def render_list(entry):
    return f'''<header><h2>{escape(entry.name)}</h2></header>
    <section data-command-file="{escape(entry.filename)}">{render_commands(entry)}</section>'''


def render_catalog(directory, catalog, root):
    tabs, panels = [], []
    for index, entry in enumerate(catalog):
        tab, panel = f"{root}-tab-{index}", f"{root}-panel-{index}"
        selected = "true" if index == 0 else "false"
        active = " active" if index == 0 else ""
        hidden = " hidden" if index else ""
        label = escape(entry.name)
        tabs.append(f'''<button class="nav-link{active}" type="button" role="tab" id="{tab}"
          aria-controls="{panel}" aria-selected="{selected}">{label}</button>''')
        panels.append(
            f'<section data-command-file="{escape(entry.filename)}" id="{panel}" role="tabpanel" aria-labelledby="{tab}"{hidden}>'
            f'{render_commands(entry)}</section>'
        )
    content = "\n".join(panels) or '<p class="text-muted">目录中没有 JSON 文件。</p>'
    tablist = f'<div class="nav nav-pills" role="tablist" aria-label="命令文件">{" ".join(tabs)}</div>' if tabs else ""
    return f'''<header><h2>命令列表</h2><p class="text-small text-muted">{escape(str(directory))}</p></header>
    {tablist}
    {content}'''


def render_settings(directory, root):
    field = f"{root}-directory"
    return f'''<header><h2>命令设置</h2></header>
    <div data-settings>
      <label class="form-label" for="{field}">命令目录</label>
      <div class="form-controls">
        <input id="{field}" class="form-control" name="directory" type="text" value="{escape(str(directory or ''))}" required spellcheck="false">
        <button type="button" class="btn btn-primary">保存</button>
      </div>
      <p class="text-small" data-status role="status"></p>
      <label class="form-label" data-manual hidden>复制后发送到当前聊天<textarea class="form-control" rows="3" readonly></textarea></label>
    </div>'''


def render_file_picker(directory, files, current, root):
    header = '<header><h2>选择命令文件</h2></header>'
    if not files:
        return f'{header}<p class="text-muted">目录中没有 JSON 文件。</p>'
    field = f"{root}-file"
    options = ['<option value="" disabled>请选择</option>']
    for path in files:
        selected = " selected" if path.name == current else ""
        name = escape(path.name)
        options.append(f'<option value="{name}"{selected}>{name}</option>')
    if not any(path.name == current for path in files):
        options[0] = '<option value="" disabled selected>请选择</option>'
    return f'''{header}
    <div data-file-selection data-directory="{escape(str(directory))}">
      <label class="form-label" for="{field}">命令文件</label>
      <div class="form-controls">
        <select id="{field}" class="form-select" required>{"".join(options)}</select>
        <button type="button" class="btn btn-primary">确定</button>
      </div>
      <p class="text-small" data-status role="status"></p>
      <label class="form-label" data-manual hidden>复制后发送到当前聊天<textarea class="form-control" rows="3" readonly></textarea></label>
    </div>'''


def print_catalog(catalog):
    if not catalog:
        print("目录中没有 JSON 文件。")
    for entry in catalog:
        variables, commands, info = entry.variables, entry.commands, entry.info
        print(f"\n{entry.name}")
        if entry.error:
            print(f"读取失败。{entry.error}")
        if isinstance(info, str):
            _, text = render_group_html(info, partial(format_group_info, variables=variables))
            if text:
                print(f"- {text}")
        else:
            for item in info:
                print(f"- {format_group_info(item, variables)}")
        if not entry.error and not commands:
            print("此文件没有命令。")
        for command in commands:
            if isinstance(command, dict):
                print(f"- {command.get('label') or command.get('id')}  {command.get('template', '')}")


def atomic_write(path, content):
    with NamedTemporaryFile(mode="w", dir=path.parent, encoding="utf-8", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def read_state(path):
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, None
    if not isinstance(config, dict):
        raise ValueError("命令设置必须使用 JSON 对象。")
    return command_directory(config.get("directory")), config.get("file")


def write_state(path, directory, selected):
    config = {"directory": str(directory)}
    if selected:
        config["file"] = selected
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(config, ensure_ascii=False) + "\n")


def read_request():
    request = json.load(sys.stdin)
    if not isinstance(request, dict):
        raise ValueError("请求必须使用 JSON 对象。")
    return request


def record_command_change(mode, directory, database, day, request):
    path = selected_command_file(directory, request.get("file"))
    entry = read_commands(path)
    if entry.error:
        raise ValueError(entry.error)
    command_id = request.get("command")
    matches = [command for command in entry.commands if isinstance(command, dict) and command.get("id") == command_id]
    if not isinstance(command_id, str) or not command_id or len(matches) != 1:
        raise ValueError("找不到唯一的记录命令。")
    request_id = request.get("requestId")
    if not isinstance(request_id, str) or not request_id:
        raise ValueError("请求缺少编号。")
    group = str(path.resolve())
    if mode == "reset":
        name = reset_variable(matches[0], entry.variables)
        if name is None:
            raise ValueError("此命令未配置重置变量。")
        recorded, total = record_reset(database, group, day, name, request_id)
        message = "已重置"
    else:
        rule = increment_rule(matches[0], entry.variables)
        if rule is None:
            raise ValueError("此命令未配置累加变量。")
        name = rule["variable"]
        amount = request.get("amount")
        if not isinstance(amount, str):
            raise ValueError("累加请求缺少数量。")
        recorded, total = record_increment(database, group, day, name, amount, request_id)
        message = "已记录"
    label = entry.variables[name].get("label") or name
    print(f'{message if recorded else "已处理该记录"}。今天{label}：{total}。')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("settings", "save", "init", "select", "list", "list-all", "increment", "reset"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--text", action="store_true")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    state = output / STATE_FILENAME
    database = output / ".chat-actions-totals.sqlite3"
    day = (args.date or date.today()).isoformat()
    try:
        if args.mode == "save":
            new_directory = command_directory(read_request().get("directory"))
            with scandir(new_directory):
                pass
            try:
                directory, selected = read_state(state)
            except (UnicodeError, ValueError):
                directory, selected = None, None
            write_state(state, new_directory, selected if new_directory == directory else None)
            print(f"已更新命令目录「{new_directory}」。")
            return

        directory, selected = read_state(state)
        if directory is None and args.mode != "settings":
            raise ValueError("请先用 #setting 配置命令目录。")

        if args.mode in ("increment", "reset"):
            record_command_change(args.mode, directory, database, day, read_request())
            return

        if args.mode == "select":
            request = read_request()
            if command_directory(request.get("directory")) != directory:
                raise ValueError("命令目录已更改，请用 #init 重新选择。")
            path = selected_command_file(directory, request.get("file"))
            write_state(state, directory, path.name)
            print(f"已更新命令文件为「{path.name}」。用 #ls 查看此文件的命令。")
            return

        root = f"chat-actions-{uuid4().hex}"
        if args.mode == "settings":
            if args.text:
                print(directory or "尚未配置命令目录。")
                return
            markup = render_settings(directory, root)
        elif args.mode == "init":
            files = command_files(directory)
            if args.text:
                print(directory)
                if not files:
                    print("目录中没有 JSON 文件。")
                for path in files:
                    suffix = "（当前选择）" if path.name == selected else ""
                    print(f"- {path.name}{suffix}")
                return
            markup = render_file_picker(directory, files, selected, root)
        elif args.mode == "list":
            path = selected_command_file(directory, selected)
            entry = read_commands(path, read_totals(database, str(path.resolve()), day))
            if args.text:
                print_catalog([entry])
                return
            markup = render_list(entry)
        else:
            catalog = [read_commands(path, read_totals(database, str(path.resolve()), day))
                       for path in command_files(directory)]
            if args.text:
                print(directory)
                print_catalog(catalog)
                return
            markup = render_catalog(directory, catalog, root)

        css = (ASSETS / "card.css").read_text(encoding="utf-8").replace("__ROOT__", root)
        script = (ASSETS / "card.js").read_text(encoding="utf-8").replace("__ROOT__", root)
        fragment = f'<div id="{root}" lang="zh-CN">{markup}</div>\n<style>\n{css}</style>\n<script>\n{script}</script>\n'
        if len(fragment.encode("utf-8")) > 1_000_000:
            raise ValueError("内容超过聊天视图容量，请使用文字模式。")
        output.mkdir(parents=True, exist_ok=True)
        path = output / f"{root}-{args.mode}.html"
        atomic_write(path, fragment)
        print(path)
    except (OSError, UnicodeError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
