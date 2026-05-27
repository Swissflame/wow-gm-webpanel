import re
from dataclasses import dataclass, asdict
from pathlib import PurePosixPath
from .ssh_service import SSHClient, shell_quote


@dataclass
class ConfigOption:
    file: str
    category: str
    key: str
    value: str
    default: str | None
    description: str
    type: str
    line: int
    sensitive: bool = False


CONF_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*=\s*(.*?)\s*$")


def guess_type(key: str, value: str) -> str:
    lower = key.lower()
    if any(word in lower for word in ["password", "secret", "key"]):
        return "password"
    if value.strip().lower() in {"0", "1", "true", "false", "yes", "no"}:
        return "boolean"
    if re.fullmatch(r"-?\d+(\.\d+)?", value.strip()):
        return "number"
    if "/" in value or "\\" in value:
        return "path"
    return "text"


def scan_content(path: str, content: str) -> list[ConfigOption]:
    options = []
    comments: list[str] = []
    category = PurePosixPath(path).name
    for index, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith(";"):
            text = stripped.lstrip("#;").strip()
            if text:
                comments.append(text)
                if text.startswith("[") and text.endswith("]"):
                    category = text.strip("[]")
            continue
        match = CONF_RE.match(line)
        if not match:
            if stripped:
                comments = []
            continue
        key, value = match.group(1), match.group(2)
        description = "\n".join(comments[-8:])
        default = None
        for comment in reversed(comments):
            m = re.search(r"(?:Default|Standard|Def\.?)\s*:?\s*([^\s]+)", comment, re.I)
            if m:
                default = m.group(1)
                break
        typ = guess_type(key, value)
        options.append(ConfigOption(path, category, key, value, default, description, typ, index, typ == "password"))
        comments = []
    return options


def discover_remote_configs(ssh: SSHClient, roots: list[str]) -> list[str]:
    parts = " ".join(shell_quote(root) for root in roots)
    code, out, err = ssh.run(f"find {parts} -type f -name '*.conf' 2>/dev/null | sort", timeout=20)
    if code != 0 and not out:
        raise RuntimeError(err)
    return [line.strip() for line in out.splitlines() if line.strip()]


def scan_remote(ssh: SSHClient, roots: list[str]) -> list[dict]:
    scanned = []
    for path in discover_remote_configs(ssh, roots):
        try:
            content = ssh.read_file(path)
            scanned.extend(asdict(item) for item in scan_content(path, content))
        except Exception as exc:
            scanned.append({"file": path, "category": "Fehler", "key": "__error__", "value": str(exc), "default": None, "description": "", "type": "text", "line": 0, "sensitive": False})
    return scanned


def update_value(content: str, key: str, new_value: str) -> str:
    lines = content.splitlines()
    pattern = re.compile(rf"^(\s*{re.escape(key)}\s*=\s*)(.*?)(\s*)$")
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = pattern.sub(rf"\g<1>{new_value}\g<3>", line)
            return "\n".join(lines) + "\n"
    raise KeyError(key)
