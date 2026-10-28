"""
deploy_to_hermes.py
Siirtää ja asentaa VELA Agent Workbenchin Proxmox Hermes AI -virtuaalikoneelle (192.168.221.189).
Konfiguroi:
1. Python-virtuaaliympäristön ja Node.js frontendin
2. FastMCP-työkalun (vela_quant) Hermes AI -agentille
3. Systemd-taustapalvelun (vela-workbench.service) 24/7 suoritukseen
4. Nginx Proxy Manager -käänteisvälityksen (chart.lan.ikkala.com -> 192.168.221.189:5173)
5. MikroTik DNS -staattisen A-tietueen (chart.lan.ikkala.com -> 192.168.222.192)
"""

import sys
import os
import tarfile
import tempfile
import time
import base64
from pathlib import Path
import paramiko
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent.resolve()
KOTIVERKKO_SECRETS = BASE_DIR.parent / "kotiverkko" / ".secrets"

def get_secrets():
    secrets = {}
    if KOTIVERKKO_SECRETS.exists():
        with open(KOTIVERKKO_SECRETS, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    secrets[k.strip()] = v.strip()
    return secrets

def create_tarball() -> Path:
    temp_tar = Path(tempfile.gettempdir()) / "vela_workbench_pkg.tar.gz"
    print(f"📦 1. Pakataan VELA Agent Workbench ({temp_tar.name})...")
    
    exclude_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "scratch", ".gemini"}
    exclude_exts = {".pyc", ".tar.gz"}
    
    with tarfile.open(temp_tar, "w:gz") as tar:
        for item in BASE_DIR.iterdir():
            if item.name in exclude_dirs:
                continue
            if item.is_file():
                if item.suffix in exclude_exts:
                    continue
                tar.add(item, arcname=item.name)
            elif item.is_dir():
                for sub in item.rglob("*"):
                    if any(p in exclude_dirs for p in sub.parts):
                        continue
                    if sub.suffix in exclude_exts:
                        continue
                    rel = sub.relative_to(BASE_DIR)
                    tar.add(sub, arcname=str(rel).replace("\\", "/"))
    print(f"✅ Pakattu ({temp_tar.stat().st_size // 1024} KB).")
    return temp_tar

def run_ssh_cmd(ssh, cmd, sudo_pass=None):
    env_prefix = 'export PATH="/home/user/.local/bin:/home/user/.hermes/node/bin:/home/user/.hermes/tools/node-26.12.1-linux-x64/bin:/home/user/.hermes/tools/npm-12.0.2-linux-x64/bin:/usr/local/bin:$PATH"; '
    if sudo_pass and cmd.startswith("sudo "):
        clean_cmd = cmd[5:]
        full_cmd = f"echo '{sudo_pass}' | sudo -S bash -c '{env_prefix}{clean_cmd}'"
    else:
        full_cmd = f"{env_prefix}{cmd}"
        
    stdin, stdout, stderr = ssh.exec_command(full_cmd)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    return exit_status, out, err

def deploy_hermes():
    sec = get_secrets()
    host = sec.get("HERMES_HOST", "192.168.221.189")
    user = sec.get("HERMES_USER", "user")
    pwd = sec.get("HERMES_PASS", "ruLma")

    print(f"\n🚀 2. Yhdistetään Hermes VM:ään ({host})...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pwd, timeout=10)

    tar_path = create_tarball()
    remote_tmp = "/tmp/vela_workbench_pkg.tar.gz"
    print("🚚 3. Siirretään projektipaketti SFTP:llä...")
    sftp = ssh.open_sftp()
    sftp.put(str(tar_path), remote_tmp)
    sftp.close()

    remote_app_dir = "/home/user/VELA-AGENT-WORKBENCH"
    print(f"📂 4. Puretaan kohteeseen {remote_app_dir}...")
    run_ssh_cmd(ssh, f"mkdir -p {remote_app_dir}")
    run_ssh_cmd(ssh, f"tar -xzf {remote_tmp} -C {remote_app_dir}")
    run_ssh_cmd(ssh, f"rm -f {remote_tmp}")

    print("🐍 5. Asennetaan Python-virtuaaliympäristö ja riippuvuudet...")
    setup_py = [
        f"test -d {remote_app_dir}/.venv || python3 -m venv {remote_app_dir}/.venv",
        f"{remote_app_dir}/.venv/bin/pip install --upgrade pip",
        f"{remote_app_dir}/.venv/bin/pip install -r {remote_app_dir}/backend/requirements.txt"
    ]
    for c in setup_py:
        print(f"   -> {c.split()[0]}...")
        status, out, err = run_ssh_cmd(ssh, c)
        if status != 0:
            print(f"❌ Virhe Python-asennuksessa: {c}\n{err}")
            ssh.close()
            sys.exit(1)

    print("⚡ 6. Asennetaan Frontend-riippuvuudet ja käännetään...")
    setup_npm = [
        f"npm --prefix {remote_app_dir}/frontend install",
        f"npm --prefix {remote_app_dir}/frontend run build"
    ]
    for c in setup_npm:
        print(f"   -> {c.split()[0]}...")
        status, out, err = run_ssh_cmd(ssh, c)
        if status != 0:
            print(f"❌ Virhe npm-asennuksessa: {c}\n{err}")
            ssh.close()
            sys.exit(1)

    print("⚙️ 7. Konfiguroidaan FastMCP Antigravity / Hermes -agentille...")
    mcp_config_script = f"""
import json, os
cfg_dir = os.path.expanduser('~/.gemini/config')
os.makedirs(cfg_dir, exist_ok=True)
cfg_path = os.path.join(cfg_dir, 'mcp_config.json')
data = {{'mcpServers': {{}}}}
if os.path.exists(cfg_path):
    try:
        with open(cfg_path, 'r') as f:
            data = json.load(f)
            if not isinstance(data, dict) or 'mcpServers' not in data:
                data = {{'mcpServers': {{}}}}
    except Exception:
        data = {{'mcpServers': {{}}}}

data['mcpServers']['vela_quant'] = {{
    'command': '{remote_app_dir}/.venv/bin/python',
    'args': ['{remote_app_dir}/backend/server.py'],
    'env': {{
        'PYTHONUNBUFFERED': '1',
        'PYTHONPATH': '{remote_app_dir}:{remote_app_dir}/backend',
        'BRIDGE_HTTP_URL': 'http://127.0.0.1:8765'
    }},
    'disabled': False
}}
with open(cfg_path, 'w') as f:
    json.dump(data, f, indent=2)
print('FastMCP konfiguroitu:', cfg_path)
"""
    run_ssh_cmd(ssh, f"python3 -c \"{mcp_config_script}\"")

    print("⚙️ 8. Luodaan ja käynnistetään systemd-palvelu (vela-workbench.service)...")
    service_content = f"""[Unit]
Description=VELA Agent Workbench Service (Bridge + Frontend)
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={remote_app_dir}
ExecStart=/bin/bash {remote_app_dir}/run.sh
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=PORT=5173
Environment=BRIDGE_PORT=8765

[Install]
WantedBy=multi-user.target
"""
    remote_svc_tmp = "/tmp/vela-workbench.service"
    sftp = ssh.open_sftp()
    with sftp.file(remote_svc_tmp, "w") as f:
        f.write(service_content)
    sftp.close()

    svc_cmds = [
        f"sudo cp {remote_svc_tmp} /etc/systemd/system/vela-workbench.service",
        f"sudo rm -f {remote_svc_tmp}",
        "sudo systemctl daemon-reload",
        "sudo systemctl enable vela-workbench",
        "sudo systemctl restart vela-workbench"
    ]
    for c in svc_cmds:
        status, out, err = run_ssh_cmd(ssh, c, sudo_pass=pwd)
        if status != 0:
            print(f"❌ Virhe systemd-palvelun asetuksessa: {c}\n{err}")
            ssh.close()
            sys.exit(1)

    print("⏳ 9. Odotetaan 4 sekuntia palveluiden heräämistä...")
    time.sleep(4)

    status, out, err = run_ssh_cmd(ssh, "systemctl status vela-workbench --no-pager")
    print("\n--- Palvelun tila Hermeksellä ---")
    print(out[:400])

    status, out, err = run_ssh_cmd(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5173/")
    print(f"\n📡 Frontend HTTP-testi (Hermes 127.0.0.1:5173): Status {out}")
    status, out, err = run_ssh_cmd(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8765/api/health")
    print(f"📡 Bridge HTTP-testi (Hermes 127.0.0.1:8765/api/health): Status {out}")

    ssh.close()

def configure_npm():
    print("\n🌐 10. Konfiguroidaan Nginx Proxy Manager (chart.lan.ikkala.com)...")
    sec = get_secrets()
    npm_host = sec.get("NPM_HOST", "192.168.222.192")
    npm_user = "ikkala@gmail.com"
    npm_pass = "ruLmaruLma"

    try:
        r_tok = requests.post(f"http://{npm_host}:81/api/tokens", json={"identity": npm_user, "secret": npm_pass}, timeout=5)
        token = r_tok.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}

        hosts = requests.get(f"http://{npm_host}:81/api/nginx/proxy-hosts", headers=headers, timeout=5).json()
        target_domain = "chart.lan.ikkala.com"
        existing_host = None
        for h in hosts:
            if target_domain in h.get("domain_names", []):
                existing_host = h
                break

        proxy_payload = {
            "domain_names": ["chart.lan.ikkala.com"],
            "forward_scheme": "http",
            "forward_host": "192.168.221.189",
            "forward_port": 5173,
            "certificate_id": 1,
            "ssl_forced": 1,
            "hsts_enabled": 1,
            "hsts_subdomains": 0,
            "http2_support": 1,
            "block_exploits": 1,
            "caching_enabled": 0,
            "allow_websocket_upgrade": 1,
            "access_list_id": 0,
            "advanced_config": "",
            "meta": {"letsencrypt_agree": False, "dns_challenge": False}
        }

        if existing_host:
            hid = existing_host["id"]
            print(f"   Päivitetään olemassa oleva Proxy Host (ID {hid})...")
            r_up = requests.put(f"http://{npm_host}:81/api/nginx/proxy-hosts/{hid}", headers=headers, json=proxy_payload, timeout=5)
            print("   Vaste:", r_up.status_code)
        else:
            print("   Luodaan uusi Proxy Host: chart.lan.ikkala.com -> 192.168.221.189:5173...")
            r_cr = requests.post(f"http://{npm_host}:81/api/nginx/proxy-hosts", headers=headers, json=proxy_payload, timeout=5)
            print("   Vaste:", r_cr.status_code)

        # Reload nginx
        p_host = sec.get("PROXMOX_HOST", "192.168.222.190")
        p_pass = sec.get("PROXMOX_PASS")
        ssh_p = paramiko.SSHClient()
        ssh_p.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_p.connect(p_host, username='root', password=p_pass, timeout=10)
        ssh_p.exec_command("pct exec 101 -- docker exec npm_app_1 nginx -t && pct exec 101 -- docker exec npm_app_1 nginx -s reload")
        ssh_p.close()
        print("   ✅ NPM reititys ja SSL aktivoitu.")
    except Exception as e:
        print(f"⚠️ Virhe NPM-konfiguroinnissa: {e}")

def configure_mikrotik_dns():
    print("\n📍 11. Konfiguroidaan MikroTik DNS...")
    sec = get_secrets()
    auth_str = f"{sec['MIKROTIK_USER']}:{sec['MIKROTIK_PASS']}"
    headers = {
        "Authorization": f"Basic {base64.b64encode(auth_str.encode()).decode()}",
        "Content-Type": "application/json"
    }
    router_url = f"http://{sec['MIKROTIK_HOST']}/rest/ip/dns/static"
    try:
        resps = requests.get(router_url, headers=headers, timeout=5).json()
        names = {r.get("name") for r in resps if "name" in r}
        target = "chart.lan.ikkala.com"
        if target not in names:
            print(f"   Lisätään staattinen A-tietue: {target} -> 192.168.222.192...")
            requests.put(router_url, headers=headers, json={
                "name": target,
                "address": "192.168.222.192",
                "comment": "VELA Agent Workbench via NPM",
                "ttl": "1d"
            }, timeout=5)
        else:
            print(f"   Tietue {target} on jo olemassa MikroTikissä.")
        print("   ✅ MikroTik DNS ajan tasalla.")
    except Exception as e:
        print(f"⚠️ Virhe DNS-konfiguroinnissa: {e}")

def verify_live():
    print("\n🔍 12. Varmistetaan pääsy palveluun...")
    import urllib3
    urllib3.disable_warnings()
    time.sleep(2)
    urls = [
        "http://192.168.221.189:5173",
        "https://chart.lan.ikkala.com"
    ]
    for u in urls:
        try:
            r = requests.get(u, timeout=5, verify=False)
            print(f"   {u} -> Status {r.status_code} ✅")
        except Exception as e:
            print(f"   {u} -> {e}")

def main():
    deploy_hermes()
    configure_npm()
    configure_mikrotik_dns()
    verify_live()
    print("\n" + "=" * 60)
    print("🎉 VELA AGENT WORKBENCH ON VALMIINA HERMEKSELLÄ!")
    print("👉 HTTPS-osoite:   https://chart.lan.ikkala.com")
    print("👉 Suora lähiverkko: http://192.168.221.189:5173")
    print("=" * 60)

if __name__ == "__main__":
    main()
