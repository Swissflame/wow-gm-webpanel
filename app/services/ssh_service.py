import socket
import time
from pathlib import PurePosixPath
import paramiko


def test_port(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


class SSHClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def _connect(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            self.cfg["wow_host"],
            port=int(self.cfg.get("ssh_port", 22)),
            username=self.cfg["ssh_user"],
            password=self.cfg.get("ssh_password") or None,
            timeout=10,
            look_for_keys=False,
        )
        return client

    def run(self, command: str, timeout: int = 30) -> tuple[int, str, str]:
        with self._connect() as client:
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            return stdout.channel.recv_exit_status(), stdout.read().decode(errors="replace"), stderr.read().decode(errors="replace")

    def read_file(self, path: str) -> str:
        code, out, err = self.run(f"sudo -n cat {shell_quote(path)} || cat {shell_quote(path)}", timeout=10)
        if code != 0:
            raise RuntimeError(err or out)
        return out

    def write_file(self, path: str, content: str):
        marker = f"EOF_{int(time.time())}"
        target = shell_quote(path)
        command = (
            f"cat > /tmp/wowpanel_upload <<'{marker}'\n{content}\n{marker}\n"
            f"cp /tmp/wowpanel_upload {target} || sudo -n cp /tmp/wowpanel_upload {target}\n"
            "rc=$?\nrm -f /tmp/wowpanel_upload\nexit $rc"
        )
        return self.run(command, timeout=30)

    def service_action(self, pattern: str, action: str) -> tuple[int, str, str]:
        path = PurePosixPath(pattern)
        workdir = str(path.parent)
        binary = path.name
        log = f"/tmp/{binary}.wowpanel.log"
        process_script = f"""
find_pids() {{
  for pid in $(pgrep -x {shell_quote(binary)} || true); do
    if [ "$(readlink -f /proc/$pid/cwd 2>/dev/null)" = {shell_quote(workdir)} ]; then
      echo "$pid"
    fi
  done
}}
"""
        stop_script = """
for pid in $(find_pids); do kill -TERM "$pid" || true; done
for i in $(seq 1 60); do
  [ -z "$(find_pids)" ] && break
  sleep 1
done
for pid in $(find_pids); do kill -KILL "$pid" || true; done
sleep 2
"""
        start_script = f"cd {shell_quote(workdir)} && nohup ./{binary} >{shell_quote(log)} 2>&1 & echo started"
        script = {
            "status": process_script + "find_pids | xargs -r ps -fp || true",
            "stop": process_script + stop_script + "echo stopped",
            "start": start_script,
            "restart": process_script + stop_script + start_script,
        }[action]
        return self.run(script, timeout=90)


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
