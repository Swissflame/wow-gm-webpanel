import socket
import time
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
        command = f"cat > /tmp/wowpanel_upload <<'{marker}'\n{content}\n{marker}\nsudo cp /tmp/wowpanel_upload {shell_quote(path)} && rm /tmp/wowpanel_upload"
        return self.run(command, timeout=30)

    def service_action(self, pattern: str, action: str) -> tuple[int, str, str]:
        script = {
            "status": f"pgrep -af {shell_quote(pattern)} || true",
            "stop": f"pkill -TERM -f {shell_quote(pattern)}",
            "start": f"nohup {pattern} >/tmp/{pattern.split('/')[-1]}.log 2>&1 &",
            "restart": f"pkill -TERM -f {shell_quote(pattern)} || true; sleep 3; nohup {pattern} >/tmp/{pattern.split('/')[-1]}.log 2>&1 &",
        }[action]
        return self.run(script, timeout=20)


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
