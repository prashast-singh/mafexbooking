"""Upload a binary file to remote host over SSH when scp/sftp are disabled."""
from __future__ import annotations

import base64
import shlex
import subprocess
import sys
from pathlib import Path

CHUNK = 48_000


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: upload_over_ssh.py <local_file> <ssh_target> <remote_path>")
        return 1
    local = Path(sys.argv[1])
    target = sys.argv[2]
    remote = sys.argv[3]
    data = local.read_bytes()
    ssh_base = [
        "ssh",
        "-i",
        r"C:\Users\Singhpr4_u\bookingServerSSHKey",
        "-o",
        "StrictHostKeyChecking=no",
        target,
    ]
    subprocess.run(ssh_base + [f"rm -f {remote}"], check=True)
    for i in range(0, len(data), CHUNK):
        chunk_b64 = base64.b64encode(data[i : i + CHUNK]).decode("ascii")
        py = f'import base64,sys; open("{remote}","ab").write(base64.b64decode(sys.stdin.read()))'
        proc = subprocess.run(
            ssh_base + [f"python3 -c {shlex.quote(py)}"],
            input=chunk_b64,
            text=True,
            check=True,
        )
    print(f"uploaded {len(data)} bytes to {remote}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
