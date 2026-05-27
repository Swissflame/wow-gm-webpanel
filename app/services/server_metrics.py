from .ssh_service import SSHClient, test_port
from . import wowdb


def collect_server_overview(cfg: dict, realm: str) -> dict:
    ports = {
        "Authserver": {"port": int(cfg["realms"]["auth_port"]), "online": False},
        "Normal-Realm": {"port": int(cfg["realms"]["normal_world_port"]), "online": False},
        "Playerbot-Realm": {"port": int(cfg["realms"]["playerbot_world_port"]), "online": False},
    }
    for item in ports.values():
        item["online"] = test_port(cfg["server"]["wow_host"], item["port"])

    overview = {
        "ports": ports,
        "host": cfg["server"]["wow_host"],
        "system": {},
        "memory": {},
        "disks": [],
        "processes": [],
        "logs": "",
        "errors": [],
        "realm_stats": {},
    }
    try:
        overview["realm_stats"] = wowdb.dashboard_stats(cfg, realm)
    except Exception as exc:
        overview["errors"].append(f"Datenbankwerte: {exc}")

    script = r"""
echo "__HOST__"; hostname; uptime -p
echo "__LOAD__"; cat /proc/loadavg; nproc
echo "__MEM__"; free -m | awk 'NR==2{print $2 "|" $3 "|" $7}'
echo "__DISK__"; df -Pm / /opt /tmp /var/lib/mysql 2>/dev/null | awk 'NR>1{print $6 "|" $2 "|" $3 "|" $4 "|" $5}'
echo "__PROC__"; for pid in $(pgrep -x authserver; pgrep -x worldserver); do cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null || echo "?"); ps -p "$pid" -o pid=,pcpu=,pmem=,etime=,comm= | awk -v cwd="$cwd" '{$5=cwd "/" $5; print}'; done
echo "__LOGS__"; tail -n 80 /tmp/authserver.log /tmp/worldserver.log 2>/dev/null || true
"""
    try:
        code, out, err = SSHClient(cfg["server"]).run(script, timeout=12)
        if code != 0 and err:
            overview["errors"].append(err.strip())
        parse_ssh_metrics(out, overview)
    except Exception as exc:
        overview["errors"].append(f"SSH-Metriken: {exc}")
    return overview


def parse_ssh_metrics(output: str, overview: dict):
    sections = split_sections(output)
    host_lines = sections.get("HOST", [])
    if host_lines:
        overview["system"]["hostname"] = host_lines[0]
    if len(host_lines) > 1:
        overview["system"]["uptime"] = host_lines[1]

    load_lines = sections.get("LOAD", [])
    if load_lines:
        parts = load_lines[0].split()
        if len(parts) >= 3:
            overview["system"]["load1"] = float_or_zero(parts[0])
            overview["system"]["load5"] = float_or_zero(parts[1])
            overview["system"]["load15"] = float_or_zero(parts[2])
    if len(load_lines) > 1:
        overview["system"]["cpus"] = int(float_or_zero(load_lines[1]) or 1)

    mem_lines = sections.get("MEM", [])
    if mem_lines:
        total, used, available = (mem_lines[0].split("|") + ["0", "0", "0"])[:3]
        total_i = int(float_or_zero(total))
        used_i = int(float_or_zero(used))
        overview["memory"] = {
            "total": total_i,
            "used": used_i,
            "available": int(float_or_zero(available)),
            "percent": percent(used_i, total_i),
        }

    disks = []
    seen = set()
    for line in sections.get("DISK", []):
        mount, total, used, free, used_percent = (line.split("|") + ["", "0", "0", "0", "0"])[:5]
        if not mount or mount in seen:
            continue
        seen.add(mount)
        disks.append({
            "mount": mount,
            "total": int(float_or_zero(total)),
            "used": int(float_or_zero(used)),
            "free": int(float_or_zero(free)),
            "percent": int(str(used_percent).strip().rstrip("%") or 0),
        })
    overview["disks"] = disks

    processes = []
    for line in sections.get("PROC", []):
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        pid, cpu, mem, etime, args = parts
        lower_args = args.lower()
        if "authserver" in lower_args:
            name = "Authserver"
        elif "playerbot" in lower_args:
            name = "Playerbot-Realm"
        else:
            name = "Normal-Realm"
        processes.append({
            "pid": pid,
            "cpu": float_or_zero(cpu),
            "mem": float_or_zero(mem),
            "etime": etime,
            "name": name,
            "args": args,
        })
    overview["processes"] = processes
    overview["logs"] = "\n".join(sections.get("LOGS", [])).strip()


def split_sections(output: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for raw in output.splitlines():
        line = raw.rstrip()
        if line.startswith("__") and line.endswith("__"):
            current = line.strip("_")
            sections[current] = []
            continue
        if current:
            sections[current].append(line)
    return sections


def percent(value: int, total: int) -> int:
    if not total:
        return 0
    return max(0, min(100, round(value * 100 / total)))


def float_or_zero(value: str) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0
