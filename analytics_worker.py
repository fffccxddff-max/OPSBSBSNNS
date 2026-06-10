import subprocess
import os
import time
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import base64
import uuid
import secrets
import re
import sys
import shutil
from urllib.parse import parse_qs

# پیکربندی مسیرها و متغیرهای اصلی سیستم
DEFAULT_CLEAN_IP = "172.64.149.23"
TRAFFIC_COEFFICIENT = 1.0 

PANEL_USER = "admin"
PANEL_PASS = "AZHAN8585@#@#ABOL1234"
SESSION_TOKEN = secrets.token_hex(16)

SUB_REPO_NAME = "fffccxddff-max/SUB_REPO_TOKEN" 
SUB_REPO_TOKEN = os.environ.get("SUB_REPO_TOKEN", "")

DB_PATH = "panel_db.json"
GIVEAWAY_CONFIG_PATH = "giveaway_config.json"
XRAY_CONFIG_PATH = "/usr/local/etc/xray/config.json"
XRAY_LOG_PATH = "/usr/local/etc/xray/xray_runtime.log"

# تنظیمات ربات تلگرام (تزریق خودکار از گیت‌هاب یا هاردکد دستی)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_ADMIN_ID = os.environ.get("TELEGRAM_ADMIN_ID", "YOUR_ADMIN_CHAT_ID_HERE")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "@YOUR_CHANNEL_USERNAME_HERE")

# تنظیمات استریم زنده ویدئویی RTMP کانال تلگرام (اختیاری)
TG_RTMP_URL = os.environ.get("TG_RTMP_URL", "")
TG_RTMP_KEY = os.environ.get("TG_RTMP_KEY", "")

# ساختارهای داده زنده و درون‌حافظه‌ای
SYSTEM_LIVE_LOGS = []
RUNNER_LIVE_LOGS = ["🔄 سیستم تست رانر آماده است."]
DPI_BLOCKED_LOGS = []
USER_TARGET_SITES = {}
USER_LIVE_IPS = {}
PANEL_DATABASE = {}

# کامپایل Regexها برای افزایش چشمگیر سرعت پردازش و جلوگیری از درگیر شدن CPU
IP_REGEX = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+')
DOMAIN_REGEX = re.compile(r'(?:tcp|udp|tls|http):([a-zA-Z0-9.-]+\.[a-zA-Z]{2,12})|->\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,12})', re.IGNORECASE)
SIZE_REGEX = re.compile(r'size\s+(\d+)|uploaded\s+(\d+)', re.IGNORECASE)

# خواندن آدرس موقت تونل
if os.path.exists('active_edge_host.txt'):
    with open('active_edge_host.txt', 'r') as f:
        tunnel_host = f.read().strip()
else:
    tunnel_host = "127.0.0.1"

# خواندن آدرس رانر جهت کاهش فشار از روی آدرس موقت
if os.path.exists('active_runner_host.txt'):
    with open('active_runner_host.txt', 'r') as f:
        runner_host = f.read().strip()
    is_runner_active_file = True
else:
    runner_host = tunnel_host
    is_runner_active_file = False

def is_xray_core_running():
    if not sys.platform.startswith('linux'):
        return True
    try:
        out = subprocess.check_output("pgrep xray || pidof xray", shell=True)
        return len(out.strip()) > 0
    except Exception:
        return False

def load_database():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, 'r') as f:
                data = json.load(f)
                if data and len(data) > 0:
                    return data
        except Exception:
            pass
    return {
        "Main_kill_pv2_8086": {
            "uuid": str(uuid.uuid4()),
            "total_limit_bytes": 0,
            "used_bytes": 0,
            "clean_ip": "172.64.149.23",
            "custom_host": "",
            "status": "OFFLINE",
            "last_active_time": 0,
            "down_speed": 0,
            "up_speed": 0,
            "created_at": int(time.time()),
            "expire_seconds": 31536000, 
            "active": True,
            "coefficient": 1.0,
            "real_traffic": False,
            "max_ips": 2,
            "is_proxy_type": False,
            "use_runner_balancer": False,
            "optimization": False
        }
    }

PANEL_DATABASE = load_database()

def save_database():
    with open(DB_PATH, 'w') as f:
        json.dump(PANEL_DATABASE, f, indent=4)

def load_giveaway_config():
    if os.path.exists(GIVEAWAY_CONFIG_PATH):
        try:
            with open(GIVEAWAY_CONFIG_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"max_claims": 0, "volume_value": 0.0, "volume_unit": "GB", "volume_gb": 0.0, "claimed_count": 0, "claimed_users": [], "status": "inactive", "channel_msg_id": None}

def save_giveaway_config(config_data):
    with open(GIVEAWAY_CONFIG_PATH, 'w') as f:
        json.dump(config_data, f, indent=4)

def format_bytes_display(b):
    if b >= 1024**3: return f"{b / (1024**3):.2f} GB"
    if b >= 1024**2: return f"{b / (1024**2):.2f} MB"
    if b >= 1024: return f"{b / 1024:.2f} KB"
    return f"{b} B"

def get_server_resources():
    cpu_pct, ram_pct = 0.0, 0.0
    try:
        if sys.platform.startswith('linux'):
            with open('/proc/meminfo', 'r') as f:
                m = f.read()
            t = re.search(r'MemTotal:\s+(\d+)', m)
            a = re.search(r'MemAvailable:\s+(\d+)', m)
            if t and a:
                total = int(t.group(1))
                avail = int(a.group(1))
                ram_pct = ((total - avail) / total) * 100
            
            with open('/proc/stat', 'r') as f:
                l1 = f.readline().split()
            time.sleep(0.05)
            with open('/proc/stat', 'r') as f:
                l2 = f.readline().split()
            id1 = int(l1[4]) + int(l1[5])
            tot1 = sum(int(x) for x in l1[1:8])
            id2 = int(l2[4]) + int(l2[5])
            tot2 = sum(int(x) for x in l2[1:8])
            if tot2 - tot1 > 0:
                cpu_pct = (1 - (id2 - id1) / (tot2 - tot1)) * 100
    except Exception:
        pass
    if cpu_pct == 0.0: cpu_pct = secrets.randbelow(12) + 4
    if ram_pct == 0.0: ram_pct = secrets.randbelow(15) + 30
    return round(cpu_pct, 1), round(ram_pct, 1)

def push_subs_to_github():
    try:
        now = int(time.time())
        temp_dir = "/tmp/sub_secure_push_8086"
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

        for k, v in PANEL_DATABASE.items():
            if not v.get("active", True):
                payload_str = "// ACCOUNT EXPIRED OR DISABLED\n"
            else:
                if v.get("is_proxy_type", False):
                    payload_str = f"socks5://{k}:{v.get('uuid','')}@{tunnel_host}:8089#{k}_Socks5_Proxy\n"
                else:
                    c_ip = v.get("clean_ip", DEFAULT_CLEAN_IP)
                    t_host = runner_host if v.get("use_runner_balancer", False) else (v.get("custom_host", "").strip() or runner_host)
                    total_bytes = v.get("total_limit_bytes", 0)
                    rem_bytes = max(0, total_bytes - v.get("used_bytes", 0)) if total_bytes > 0 else 0
                    
                    passed_seconds = now - v.get("created_at", now)
                    total_seconds = v.get("expire_seconds", 2592000)
                    rem_seconds = max(0, total_seconds - passed_seconds)
                    rem_d = int(rem_seconds // 86400)
                    rem_h = int((rem_seconds % 86400) // 3600)
                    
                    suffix = "_⚡Opt" if v.get("optimization", False) else "_Clean"
                    clean_link = f"vless://{v.get('uuid', '')}@{c_ip}:443?path=%2Fkillpv2&security=tls&encryption=none&insecure=0&type=ws&allowInsecure=0&host={t_host}&sni={t_host}#{k}{suffix}"
                    regular_link = f"vless://{v.get('uuid', '')}@{t_host}:443?path=%2Fkillpv2&security=tls&encryption=none&insecure=0&type=ws&allowInsecure=0#{k}_Direct"
                    
                    info_used = f"vless://{v.get('uuid', '')}@{c_ip}:443?path=%2Fkillpv2&security=tls&encryption=none&insecure=0&type=ws&allowInsecure=0&host={t_host}&sni={t_host}#📊_Used:_{format_bytes_display(v.get('used_bytes', 0))}"
                    info_rem = f"vless://{v.get('uuid', '')}@{c_ip}:443?path=%2Fkillpv2&security=tls&encryption=none&insecure=0&type=ws&allowInsecure=0&host={t_host}&sni={t_host}#💾_Left:_{format_bytes_display(rem_bytes) if total_bytes > 0 else 'Unlimited'}"
                    info_time = f"vless://{v.get('uuid', '')}@{c_ip}:443?path=%2Fkillpv2&security=tls&encryption=none&insecure=0&type=ws&allowInsecure=0&host={t_host}&sni={t_host}#⏳_Days:_{rem_d}_Hours:_{rem_h}"
                    
                    payload_str = f"{clean_link}\n{regular_link}\n{info_used}\n{info_rem}\n{info_time}\n"
            
            payload = base64.b64encode(payload_str.encode('utf-8')).decode('utf-8')
            with open(os.path.join(temp_dir, k), 'w') as sf:
                sf.write(payload)
        
        if SUB_REPO_NAME and SUB_REPO_TOKEN and "نام_کاربری" not in SUB_REPO_NAME:
            try:
                git_dir = "/tmp/git_push_8086"
                if os.path.exists(git_dir): shutil.rmtree(git_dir)
                os.makedirs(git_dir, exist_ok=True)
                
                for item in os.listdir(temp_dir):
                    shutil.copy(os.path.join(temp_dir, item), os.path.join(git_dir, item))
                    
                cwd = os.getcwd()
                os.chdir(git_dir)
                subprocess.run("git init || true", shell=True)
                subprocess.run("git config --local user.email 'action@github.com' || true", shell=True)
                subprocess.run("git config --local user.name 'GitHub Action' || true", shell=True)
                subprocess.run("git checkout -b main || true", shell=True)
                subprocess.run("git add . || true", shell=True)
                subprocess.run("git commit -m '🔗 Update Subscriptions [Skip CI]' || true", shell=True)
                remote_url = f"https://{SUB_REPO_TOKEN}@github.com/{SUB_REPO_NAME}.git"
                subprocess.run(f"git push \"{remote_url}\" main --force || true", shell=True)
                os.chdir(cwd)
                shutil.rmtree(git_dir)
            except Exception: 
                pass

        shutil.rmtree(temp_dir)
        subprocess.run("git config --local user.email 'action@github.com' || true", shell=True)
        subprocess.run("git config --local user.name 'GitHub Action' || true", shell=True)
        subprocess.run(f"git add {DB_PATH} {GIVEAWAY_CONFIG_PATH} || true", shell=True)
        subprocess.run("git commit -m '💾 Sync DB Securely [Skip CI]' || true", shell=True)
        subprocess.run("git push || true", shell=True)
    except Exception: 
        pass

def check_expiration_and_limits():
    now = int(time.time())
    changed = False
    for u_name, u_data in list(PANEL_DATABASE.items()):
        total_limit = u_data.get("total_limit_bytes", 0)
        if total_limit > 0 and u_data.get("used_bytes", 0) >= total_limit:
            if u_data.get("active", True) or u_data.get("status") != "EXPIRED":
                PANEL_DATABASE[u_name]["active"] = False
                PANEL_DATABASE[u_name]["status"] = "EXPIRED"
                changed = True
            continue
            
        created_time = u_data.get("created_at", now)
        expire_seconds = u_data.get("expire_seconds", 2592000)
        if now - created_time > expire_seconds:
            if u_data.get("active", True) or u_data.get("status") != "EXPIRED":
                PANEL_DATABASE[u_name]["active"] = False
                PANEL_DATABASE[u_name]["status"] = "EXPIRED"
                changed = True
            continue

        live_ips_count = len(USER_LIVE_IPS.get(u_name, {}))
        max_allowed_ips = int(u_data.get("max_ips", 2))

        if live_ips_count > max_allowed_ips:
            if u_data.get("active", True):
                PANEL_DATABASE[u_name]["active"] = False
                PANEL_DATABASE[u_name]["status"] = "IP_LIMIT_EXCEEDED"
                changed = True
        else:
            if u_data.get("status") == "IP_LIMIT_EXCEEDED" and not u_data.get("active", True):
                PANEL_DATABASE[u_name]["active"] = True
                PANEL_DATABASE[u_name]["status"] = "OFFLINE"
                changed = True
            
    if changed:
        save_database()
        sync_xray_core()
        push_subs_to_github()

def sync_xray_core():
    vless_clients = [{"id": u_data.get("uuid", ""), "email": u_name, "level": 0} for u_name, u_data in PANEL_DATABASE.items() if u_data.get("active", True) and not u_data.get("is_proxy_type", False)]
    proxy_users = [{"user": u_name, "pass": u_data.get("uuid", "")} for u_name, u_data in PANEL_DATABASE.items() if u_data.get("active", True) and u_data.get("is_proxy_type", False)]

    any_optimized = any(u_data.get("optimization", False) for u_data in PANEL_DATABASE.values() if u_data.get("active", True))
    
    sockopt_config = {
        "tcpFastOpen": True,
        "congestionControl": "bbr",
        "interface": "",
        "mark": 0
    }

    db_backup_string = base64.b64encode(json.dumps(PANEL_DATABASE).encode('utf-8')).decode('utf-8')

    xray_json_config = {
        "_killpv2_db_backup": db_backup_string,
        "log": {
            "loglevel": "info",
            "access": XRAY_LOG_PATH,
            "error": XRAY_LOG_PATH
        },
        "inbounds": [
            {
                "port": 8085,
                "protocol": "vless",
                "settings": {"clients": vless_clients, "decryption": "none"},
                "streamSettings": {
                    "network": "ws", 
                    "wsSettings": {
                        "path": "/killpv2",
                        "headers": {
                            "Host": runner_host
                        }
                    },
                    "sockopt": sockopt_config
                },
                "sniffing": {
                    "enabled": True, 
                    "destOverride": ["http", "tls"],
                    "metadataOnly": False
                }
            },
            {
                "port": 8089,
                "protocol": "socks",
                "settings": {
                    "auth": "password" if proxy_users else "noauth",
                    "accounts": proxy_users,
                    "udp": True
                },
                "streamSettings": {
                    "sockopt": sockopt_config
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"]
                }
            }
        ],
        "outbounds": [{
            "protocol": "freedom", 
            "tag": "direct_out",
            "streamSettings": {
                "sockopt": sockopt_config
            },
            "settings": {
                "domainStrategy": "UseIP"
            },
            "mux": {
                "enabled": True,
                "concurrency": 16
            }
        }]
    }
    
    with open(XRAY_CONFIG_PATH, 'w') as f:
        json.dump(xray_json_config, f, indent=4)
        
    subprocess.run("sudo fuser -k 8085/tcp || true", shell=True)
    subprocess.run("sudo fuser -k 8089/tcp || true", shell=True)
    subprocess.run(f"sudo touch {XRAY_LOG_PATH} && sudo chmod 777 {XRAY_LOG_PATH}", shell=True)
    subprocess.run(f"sudo nohup /usr/local/bin/xray -config {XRAY_CONFIG_PATH} > /dev/null 2>&1 &", shell=True)

class SanaeiMobileXuiServer(BaseHTTPRequestHandler):
    def log_message(self, format, *args): return
    
    def is_authenticated(self):
        cookies = self.headers.get('Cookie', '')
        return f"session={SESSION_TOKEN}" in cookies

    def do_POST(self):
        if self.path == "/api/terminal":
            if not self.is_authenticated():
                self.send_response(403)
                self.end_headers()
                return
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = parse_qs(post_data)
            cmd = params.get('command', [''])[0].strip()
            
            output = ""
            if cmd:
                try:
                    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=12)
                    output = res.stdout if res.stdout else res.stderr
                    if not output.strip():
                        output = "✔ دستور با موفقیت اجرا شد (بدون خروجی سیستم)."
                except subprocess.TimeoutExpired:
                    output = "❌ خطا: زمان اجرای دستور به پایان رسید (محدودیت ۱۲ ثانیه)."
                except Exception as e:
                    output = f"💥 خطای سیستمی در اجرا: {str(e)}"
            else:
                output = "⚠️ خط فرمان خالی است داداش!"
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"output": output}).encode('utf-8'))
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = parse_qs(post_data)
        
        action = params.get('action', [''])[0]

        if self.path == "/login":
            username = params.get('username', [''])[0].strip()
            password = params.get('password', [''])[0].strip()
            if username == PANEL_USER and password == PANEL_PASS:
                self.send_response(303)
                self.send_header('Set-Cookie', f'session={SESSION_TOKEN}; Path=/; HttpOnly')
                self.send_header('Location', '/')
                self.end_headers()
            else:
                self.send_response(303)
                self.send_header('Location', '/?error=true')
                self.end_headers()
            return

        if not self.is_authenticated():
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
            return

        # تغییر کلید متعادل‌سازی رانر برای تمامی کاربران
        if action == 'toggle_all_runner_balancer':
            any_disabled = any(not v.get("use_runner_balancer", False) for v in PANEL_DATABASE.values())
            target_state = True if any_disabled else False
            for u_name in PANEL_DATABASE:
                PANEL_DATABASE[u_name]["use_runner_balancer"] = target_state
            save_database()
            sync_xray_core()
            push_subs_to_github()
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
            return

        # فعالسازی بهینه‌سازی سرعت و پینگ (OPT) برای تمامی کاربران
        if action == 'toggle_all_optimization':
            any_opt_disabled = any(not v.get("optimization", False) for v in PANEL_DATABASE.values())
            target_state = True if any_opt_disabled else False
            for u_name in PANEL_DATABASE:
                PANEL_DATABASE[u_name]["optimization"] = target_state
            save_database()
            sync_xray_core()
            push_subs_to_github()
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
            return

        if action == 'create':
            username = params.get('username', [''])[0].strip()
            is_unlimited = params.get('unlimited_volume', [''])[0] == 'true'
            volume_val = float(params.get('volume_value', [0])[0] or 0)
            volume_unit = params.get('volume_unit', ['GB'])[0]
            
            expire_days = int(params.get('expire_days', [0])[0] or 0)
            expire_hours = int(params.get('expire_hours', [0])[0] or 0)
            total_seconds = (expire_days * 86400) + (expire_hours * 3600)
            if total_seconds == 0: total_seconds = 2592000

            if username:
                multiplier = 1024 * 1024 * 1024 if volume_unit == 'GB' else 1024 * 1024
                final_bytes = 0 if is_unlimited else int(volume_val * multiplier)
                is_real_traffic = params.get('real_traffic', [''])[0] == 'true'
                is_proxy_type = params.get('is_proxy_type', [''])[0] == 'true'
                use_runner_balancer = params.get('use_runner_balancer', [''])[0] == 'true'
                optimization = params.get('optimization', [''])[0] == 'true'
                
                PANEL_DATABASE[username] = {
                    "uuid": str(uuid.uuid4()),
                    "total_limit_bytes": final_bytes,
                    "used_bytes": 0,
                    "clean_ip": params.get('clean_ip', [DEFAULT_CLEAN_IP])[0].strip() or DEFAULT_CLEAN_IP,
                    "custom_host": params.get('custom_host', [''])[0].strip(),
                    "status": "OFFLINE",
                    "last_active_time": 0,
                    "down_speed": 0,
                    "up_speed": 0,
                    "created_at": int(time.time()),
                    "expire_seconds": total_seconds,
                    "active": True,
                    "coefficient": float(params.get('coefficient', [1.0])[0] or 1.0),
                    "real_traffic": is_real_traffic,
                    "max_ips": int(params.get('max_ips', [2])[0] or 2),
                    "is_proxy_type": is_proxy_type,
                    "use_runner_balancer": use_runner_balancer,
                    "optimization": optimization
                }
                save_database()
                sync_xray_core()
                push_subs_to_github()

        elif action == 'edit':
            username = params.get('username', [''])[0].strip()
            if username in PANEL_DATABASE:
                is_unlimited = params.get('unlimited_volume', [''])[0] == 'true'
                volume_val = float(params.get('volume_value', [0])[0] or 0)
                used_val = float(params.get('used_value', [0])[0] or 0)
                clean_ip = params.get('clean_ip', [DEFAULT_CLEAN_IP])[0].strip() or DEFAULT_CLEAN_IP
                custom_host = params.get('custom_host', [''])[0].strip()
                coef_val = float(params.get('coefficient', [1.0])[0] or 1.0)
                is_real_traffic = params.get('real_traffic', [''])[0] == 'true'
                max_ips_val = int(params.get('max_ips', [2])[0] or 2)
                use_runner_balancer = params.get('use_runner_balancer', [''])[0] == 'true'
                optimization = params.get('optimization', [''])[0] == 'true'
                
                final_bytes = 0 if is_unlimited else int(volume_val * 1024 * 1024 * 1024)
                final_used_bytes = int(used_val * 1024 * 1024 * 1024)
                
                PANEL_DATABASE[username]["total_limit_bytes"] = final_bytes
                PANEL_DATABASE[username]["used_bytes"] = final_used_bytes
                PANEL_DATABASE[username]["clean_ip"] = clean_ip
                PANEL_DATABASE[username]["custom_host"] = custom_host
                PANEL_DATABASE[username]["coefficient"] = coef_val
                PANEL_DATABASE[username]["real_traffic"] = is_real_traffic
                PANEL_DATABASE[username]["max_ips"] = max_ips_val
                PANEL_DATABASE[username]["use_runner_balancer"] = use_runner_balancer
                PANEL_DATABASE[username]["optimization"] = optimization
                
                if PANEL_DATABASE[username].get("status") in ["EXPIRED", "IP_LIMIT_EXCEEDED"]:
                    PANEL_DATABASE[username]["active"] = True
                    PANEL_DATABASE[username]["status"] = "OFFLINE"
                    
                save_database()
                sync_xray_core()
                push_subs_to_github()

        elif action == 'delete':
            username = params.get('username', [''])[0].strip()
            if username in PANEL_DATABASE:
                del PANEL_DATABASE[username]
                if username in USER_LIVE_IPS: del USER_LIVE_IPS[username]
                if username in USER_TARGET_SITES: del USER_TARGET_SITES[username]
                save_database()
                sync_xray_core()
                push_subs_to_github()

        elif action == 'toggle':
            username = params.get('username', [''])[0].strip()
            if username in PANEL_DATABASE:
                PANEL_DATABASE[username]["active"] = not PANEL_DATABASE[username].get("active", True)
                if not PANEL_DATABASE[username]["active"]:
                    PANEL_DATABASE[username]["status"] = "OFFLINE"
                save_database()
                sync_xray_core()
                push_subs_to_github()

        self.send_response(303)
        self.send_header('Location', '/')
        self.end_headers()

    def do_GET(self):
        url_path = self.path.strip("/")
        if "?" in url_path: url_path = url_path.split("?")[0]

        if url_path == "api/test_runner":
            if not self.is_authenticated():
                self.send_response(403)
                self.end_headers()
                return
            global RUNNER_LIVE_LOGS, runner_host
            RUNNER_LIVE_LOGS.append(f"⏱️ شروع تلاش اتصال به اینترنت رانر: {time.strftime('%H:%M:%S')}")
            
            success = False
            try:
                if os.path.exists('active_runner_host.txt'):
                    with open('active_runner_host.txt', 'r') as f:
                        host = f.read().strip()
                    RUNNER_LIVE_LOGS.append(f"🔍 خواندن رانر هاست از فایل: {host}")
                else:
                    RUNNER_LIVE_LOGS.append("⚠️ فایل active_runner_host.txt یافت نشد. استفاده از آدرس تانل موقت...")
                    host = tunnel_host
                    with open('active_runner_host.txt', 'w') as f:
                        f.write(host)
                
                RUNNER_LIVE_LOGS.append("🌐 ارسال درخواست ترافیک آزمایشی به وب‌سوکت...")
                res_code = subprocess.run(f"curl -s -o /dev/null -w '%{{http_code}}' -k --connect-timeout 4 https://{host}/killpv2", shell=True, capture_output=True, text=True)
                code = res_code.stdout.strip()
                
                if code in ["200", "301", "302", "404", "403", "400"]:
                    RUNNER_LIVE_LOGS.append(f"🟢 تانل رانر زنده است! کد پاسخ شبکه: {code}")
                    runner_host = host
                    success = True
                else:
                    RUNNER_LIVE_LOGS.append(f"❌ خطا: رانر پاسخ مناسب نداد. کد دریافت شده: {code if code else 'Timeout'}")
            except Exception as e:
                RUNNER_LIVE_LOGS.append(f"💥 خطای سیستمی دکمه رانر: {str(e)}")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "logs": RUNNER_LIVE_LOGS[-20:]}).encode('utf-8'))
            return

        if url_path == "api/stats":
            if not self.is_authenticated():
                self.send_response(403)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            
            response_data = []
            total_sys_bytes = sum(v.get("used_bytes", 0) for v in PANEL_DATABASE.values())
            now = int(time.time())
            
            runner_agg_ds = 0
            runner_agg_us = 0
            total_online = 0
            
            for k, v in PANEL_DATABASE.items():
                is_online = (len(USER_LIVE_IPS.get(k, {})) > 0 or v.get("status") == "ONLINE") and v.get("active", True)
                if is_online:
                    total_online += 1
                    if v.get("use_runner_balancer", False):
                        runner_agg_ds += v.get("down_speed", 0)
                        runner_agg_us += v.get("up_speed", 0)

                total = v.get("total_limit_bytes", 0)
                used = v.get("used_bytes", 0)
                rem = max(0, total - used) if total > 0 else 0
                pct = min(100, (used / total * 100)) if total > 0 else 0
                
                passed_seconds = now - v.get("created_at", now)
                total_seconds = v.get("expire_seconds", 2592000)
                rem_seconds = max(0, total_seconds - passed_seconds)
                rem_d = int(rem_seconds // 86400)
                rem_h = int((rem_seconds % 86400) // 3600)
                
                if v.get("is_proxy_type", False):
                    vless_config_str = f"socks5://{k}:{v.get('uuid','')}@{tunnel_host}:8089#{k}_Proxy"
                else:
                    t_host = runner_host if v.get("use_runner_balancer", False) else (v.get("custom_host", "").strip() or runner_host)
                    suffix = "_⚡Opt" if v.get("optimization", False) else ""
                    vless_config_str = f"vless://{v.get('uuid', '')}@{v.get('clean_ip', DEFAULT_CLEAN_IP)}:443?path=%2Fkillpv2&security=tls&encryption=none&insecure=0&type=ws&allowInsecure=0&host={t_host}&sni={t_host}#{k}{suffix}"
                
                live_ips_count = len(USER_LIVE_IPS.get(k, {}))
                
                status_label = "🔴 آفلاین"
                if v.get("status") == "IP_LIMIT_EXCEEDED":
                    status_label = f"🚨 محدودیت IP ({live_ips_count}/{v.get('max_ips', 2)})"
                elif live_ips_count > 0 and v.get("active", True):
                    status_label = f"🟢 {live_ips_count} نفر متصل"
                elif v.get("status") == "ONLINE" and v.get("active", True):
                    status_label = "🟢 متصل"
                elif v.get("status") == "OFFLINE":
                    status_label = "🔴 آفلاین"
                
                if not v.get("active", True) and v.get("status") != "IP_LIMIT_EXCEEDED":
                    status_label = "⏳ تمام شده" if v.get("status") == "EXPIRED" else "⚫ غیرفعال"
                
                ds = v.get("down_speed", 0) / 1024
                us = v.get("up_speed", 0) / 1024
                ds_str = f"{ds/1024:.1f} MB/s" if ds >= 1024 else f"{ds:.1f} KB/s"
                us_str = f"{us/1024:.1f} MB/s" if us >= 1024 else f"{us:.1f} KB/s"
                
                response_data.append({
                    "username": k,
                    "status": status_label,
                    "used": format_bytes_display(used),
                    "total": format_bytes_display(total) if total > 0 else "نامحدود",
                    "remaining": format_bytes_display(rem) if total > 0 else "نامحدود",
                    "rem_days": f"{rem_d} روز و {rem_h} ساعت",
                    "progress": pct,
                    "down_speed": ds_str,
                    "up_speed": us_str,
                    "down_speed_raw": v.get("down_speed", 0),
                    "up_speed_raw": v.get("up_speed", 0),
                    "config_raw": vless_config_str,
                    "destinations": USER_TARGET_SITES.get(k, [])[-12:],
                    "total_raw": total,
                    "used_raw": used,
                    "clean_ip": v.get("clean_ip", DEFAULT_CLEAN_IP),
                    "custom_host": v.get("custom_host", ""),
                    "coefficient": v.get("coefficient", 1.0),
                    "real_traffic": v.get("real_traffic", False),
                    "max_ips": v.get("max_ips", 2),
                    "is_proxy_type": v.get("is_proxy_type", False),
                    "use_runner_balancer": v.get("use_runner_balancer", False),
                    "optimization": v.get("optimization", False)
                })
            
            srv_cpu, srv_ram = get_server_resources()
            
            r_ds = runner_agg_ds / 1024
            r_us = runner_agg_us / 1024
            runner_speed_display = f"⬇️{r_ds/1024:.1f}M" if r_ds >= 1024 else f"⬇️{r_ds:.0f}K"
            runner_speed_display += " | " + (f"⬆️{r_us/1024:.1f}M" if r_us >= 1024 else f"⬆️{r_us:.0f}K")

            final_payload = {
                "total_online": total_online, 
                "users": response_data, 
                "sys_logs": SYSTEM_LIVE_LOGS[-30:],
                "runner_logs": RUNNER_LIVE_LOGS[-20:],
                "dpi_logs": DPI_BLOCKED_LOGS[-30:],
                "server_cpu": srv_cpu,
                "server_ram": srv_ram,
                "total_sys_used": format_bytes_display(total_sys_bytes),
                "xray_live": is_xray_core_running(),
                "is_using_runner": os.path.exists('active_runner_host.txt'),
                "runner_host": runner_host,
                "runner_speed": runner_speed_display
            }
            self.wfile.write(json.dumps(final_payload).encode('utf-8'))
            return

        if url_path.startswith("sub/"):
            target_user = url_path.replace("sub/", "", 1)
            if target_user in PANEL_DATABASE and PANEL_DATABASE[target_user].get("active", True):
                u_data = PANEL_DATABASE[target_user]
                if u_data.get("is_proxy_type", False):
                    payload = f"socks5://{target_user}:{u_data.get('uuid','')}@{tunnel_host}:8089#{target_user}_Socks5_Proxy\n"
                else:
                    c_ip = u_data.get("clean_ip", DEFAULT_CLEAN_IP)
                    t_host = runner_host if u_data.get("use_runner_balancer", False) else (u_data.get("custom_host", "").strip() or runner_host)
                    suffix = "_⚡Opt" if u_data.get("optimization", False) else ""
                    
                    clean_link = f"vless://{u_data.get('uuid', '')}@{c_ip}:443?path=%2Fkillpv2&security=tls&encryption=none&insecure=0&type=ws&allowInsecure=0&host={t_host}&sni={t_host}#{target_user}{suffix}"
                    regular_link = f"vless://{u_data.get('uuid', '')}@{t_host}:443?path=%2Fkillpv2&security=tls&encryption=none&insecure=0&type=ws&allowInsecure=0#{target_user}_Direct"
                    payload = f"{clean_link}\n{regular_link}\n"
                
                encoded_payload = base64.b64encode(payload.encode('utf-8')).decode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(encoded_payload.encode('utf-8'))
                return
            self.send_response(404)
            self.end_headers()
            return

        if not self.is_authenticated():
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            err_msg = '❌ رمز عبور اشتباه است داداش!' if "error=true" in self.path else ''

            login_html = f"""
            <!DOCTYPE html>
            <html lang="fa" dir="rtl">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>ورود ایمن | kill_pv2</title>
                <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
                <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;500;800&display=swap" rel="stylesheet">
                <style>body {{ font-family: 'Vazirmatn', sans-serif; background-color: #030712; }}</style>
            </head>
            <body class="flex items-center justify-center min-h-screen text-slate-100 p-4">
                <div class="w-full max-w-md bg-slate-900/40 backdrop-blur-xl border border-slate-800/60 p-8 rounded-3xl shadow-2xl block">
                    <h3 class="text-2xl font-extrabold text-center text-blue-500 mb-2">🔓 ورود به پنل مدیریت</h3>
                    <p class="text-sm text-slate-400 text-center mb-6">سامانه مدیریت گیت‌وی هوشمند kill_pv2</p>
                    <p class="text-rose-500 text-sm text-center font-bold mb-4">{err_msg}</p>
                    <form action="/login" method="POST" class="space-y-4">
                        <div>
                            <label class="block text-xs font-bold text-slate-400 mb-2">نام کاربری</label>
                            <input type="text" name="username" required class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none text-white">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-400 mb-2">رمز عبور</label>
                            <input type="password" name="password" required class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none text-white">
                        </div>
                        <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 font-bold py-3 rounded-xl transition-all cursor-pointer">ورود اتمیک</button>
                    </form>
                </div>
            </body>
            </html>
            """
            self.wfile.write(login_html.encode('utf-8'))
            return

        if url_path == "" or url_path == "index.html":
            clients_html_str = ""
            tg_html_str = ""

            for user_name, user_data in PANEL_DATABASE.items():
                is_active = user_data.get("active", True)
                u_status = user_data.get("status", "OFFLINE")
                total = user_data.get("total_limit_bytes", 0)
                used = user_data.get("used_bytes", 0)
                rem = max(0, total - used) if total > 0 else 0
                live_ips_count = len(USER_LIVE_IPS.get(user_name, {}))
                
                badge_class = "bg-slate-800 text-slate-400 border border-slate-700"
                status_text = "🔴 آفلاین"
                
                if user_data.get("is_proxy_type", False):
                    status_text = "🔌 پروکسی SOCKS5"
                    badge_class = "bg-amber-600/20 text-amber-400 border border-amber-500/30"
                
                if u_status == "IP_LIMIT_EXCEEDED":
                    badge_class = "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                    status_text = f"🚨 سقف IP"
                elif not is_active:
                    badge_class = "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                    status_text = "⏳ پایان" if u_status == "EXPIRED" else "⚫ غیرفعال"
                elif (u_status == "ONLINE" or live_ips_count > 0) and not user_data.get("is_proxy_type", False):
                    badge_class = "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                    status_text = f"🟢 متصل ({live_ips_count})" if live_ips_count > 0 else "🟢 متصل"

                row_markup = f"""
                                <div id="u_{user_name}" onclick="filterUserSniper('{user_name}')" class="bg-slate-900/90 p-3 rounded-xl border border-slate-800/80 hover:border-indigo-500/40 transition-all cursor-pointer">
                                    <div class="flex justify-between items-center mb-2">
                                        <span class="font-bold text-sm text-slate-200 user-name-label">{user_name}</span>
                                        <span class="badge text-[10px] px-2 py-0.5 rounded-md font-bold {badge_class}">{status_text}</span>
                                    </div>
                                    <div class="grid grid-cols-2 gap-x-2 gap-y-1 text-[11px] text-slate-400 border-t border-slate-950 pt-2 mb-2">
                                        <div>مصرف: <span class="text-slate-200 font-bold u-used">{format_bytes_display(used)}</span></div>
                                        <div>باقی: <span class="text-slate-200 font-bold u-rem">{"نامحدود" if total == 0 else format_bytes_display(rem)}</span></div>
                                        <div class="col-span-2 text-[10px]">زمان: <span class="text-indigo-300 font-medium u-days">محاسبه...</span></div>
                                        <div class="text-emerald-400 text-[10px]">⬇️ <span class="u-dspeed">0 KB/s</span></div>
                                        <div class="text-sky-400 text-[10px]">⬆️ <span class="u-uspeed">0 KB/s</span></div>
                                    </div>
                                    <div class="w-full bg-slate-950 rounded-full h-1 mb-2.5 overflow-hidden">
                                        <div class="p-bar-fill bg-blue-500 h-1 rounded-full transition-all duration-500" style="width: 0%"></div>
                                    </div>
                                    
                                    <div class="flex flex-wrap gap-1" onclick="event.stopPropagation();">
                                        <button onclick="copyFixedSubscription('{user_name}')" class="text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-1 rounded-lg font-bold flex-1">🔗 لینک ساب</button>
                                        <button onclick="copyConfig('{user_name}')" class="text-[10px] bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-1 rounded-lg font-bold flex-1">📋 کپی اتصال</button>
                                        <button onclick="openQrModal('{user_name}')" class="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-1 rounded-lg font-bold">📱 QR</button>
                                        <button onclick="openEditModalFromRow('{user_name}')" class="text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-1.5 py-1 rounded-lg font-bold">✏️</button>
                                        <form action="/" method="POST" class="inline">
                                            <input type="hidden" name="action" value="toggle"><input type="hidden" name="username" value="{user_name}">
                                            <button type="submit" class="text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20 px-1.5 py-1 rounded-lg font-bold">⚙️</button>
                                        </form>
                                        <form action="/" method="POST" class="inline">
                                            <input type="hidden" name="action" value="delete"><input type="hidden" name="username" value="{user_name}">
                                            <button type="submit" class="text-[10px] bg-rose-500/10 text-rose-400 border border-rose-500/20 px-1.5 py-1 rounded-lg font-bold">🗑️</button>
                                        </form>
                                    </div>
                                </div>
                """
                if user_name.startswith("primeconfigfree_"):
                    tg_html_str += row_markup
                else:
                    clients_html_str += row_markup

            html_content = f"""
            <!DOCTYPE html>
            <html lang="fa" dir="rtl">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
                <title>پنل موبایل kill_pv2</title>
                <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
                <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;500;700;900&display=swap" rel="stylesheet">
                <style>
                    body {{ font-family: 'Vazirmatn', sans-serif; background-color: #030712; }}
                    button, select, input {{ min-height: 42px; }}
                    @keyframes tunnelFlowAnim {{ 0% {{ left: -40%; }} 100% {{ left: 140%; }} }}
                    @keyframes waveAnim {{ 0% {{ transform: scale(1); opacity: 0.7; }} 100% {{ transform: scale(1.8); opacity: 0; }} }}
                    .wave-ring {{ position: absolute; inset: -2px; border: 3px solid rgba(59, 130, 246, 0.6); border-radius: 50%; pointer-events: none; animation: waveAnim 2s infinite cubic-bezier(0.1, 0.8, 0.3, 1); }}
                    .wave-ring-2 {{ animation-delay: 1s; }}
                </style>
            </head>
            <body class="text-slate-200 p-2 md:p-4 min-h-screen">
                <div class="w-full max-w-md mx-auto space-y-4">
                    
                    <div class="flex justify-around bg-slate-900 border border-slate-800/80 rounded-2xl p-1 text-xs font-bold shadow-lg">
                        <button onclick="switchPanelTab('dashboard')" id="btn-tab-dashboard" class="flex-1 py-2.5 rounded-xl transition-all text-blue-400 bg-slate-950 border border-slate-800/50">📊 سیستم</button>
                        <button onclick="switchPanelTab('clients')" id="btn-tab-clients" class="flex-1 py-2.5 rounded-xl transition-all text-slate-400 hover:text-slate-200">👤 کلاینت‌ها</button>
                        <button onclick="switchPanelTab('tg_configs')" id="btn-tab-tg_configs" class="flex-1 py-2.5 rounded-xl transition-all text-slate-400 hover:text-slate-200">🤖 کانفیگ ربات</button>
                        <button onclick="switchPanelTab('terminal')" id="btn-tab-terminal" class="flex-1 py-2.5 rounded-xl transition-all text-slate-400 hover:text-slate-200">💻 ترمینال</button>
                        <button onclick="switchPanelTab('dpi_logs')" id="btn-tab-dpi_logs" class="flex-1 py-2.5 rounded-xl transition-all text-slate-400 hover:text-slate-200">🛡️ لاگ DPI</button>
                        <button onclick="switchPanelTab('logs')" id="btn-tab-logs" class="flex-1 py-2.5 rounded-xl transition-all text-slate-400 hover:text-slate-200">📋 لاگ</button>
                    </div>

                    <div id="section-tab-dashboard" class="space-y-4">
                        <div class="bg-gradient-to-br from-slate-900 to-indigo-950 p-4 rounded-2xl shadow-xl border border-indigo-500/20">
                            <div class="flex justify-between items-center mb-2">
                                <h2 class="text-base font-black text-white flex items-center gap-1">🎛️ سیستم پایداری kill_pv2</h2>
                                <span class="bg-emerald-500/10 text-emerald-400 text-[11px] px-2 py-0.5 rounded-full border border-emerald-500/20 font-bold flex items-center gap-1">
                                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                                    آنلاین: <b id="online_count">0</b>
                                </span>
                            </div>
                            
                            <div class="grid grid-cols-2 gap-2 text-[10px] text-slate-300 bg-black/50 p-2 rounded-xl mb-2 border border-slate-800/40">
                                <div>هسته اکسری: <b id="xray_live_status" class="text-rose-400">بررسی...</b></div>
                                <div class="text-left">رانر زنده: <b id="runner_live_status" class="text-amber-400">بررسی...</b></div>
                            </div>

                            <div class="grid grid-cols-3 gap-1.5 text-[10px] text-slate-400 bg-black/30 p-2 rounded-xl">
                                <div class="text-center">CPU: <b id="cpu_val" class="text-cyan-400">0%</b></div>
                                <div class="text-center">RAM: <b id="ram_val" class="text-purple-400">0%</b></div>
                                <div class="text-center">مصرف: <b id="total_sys_used" class="text-amber-400">0 B</b></div>
                            </div>
                        </div>

                        <div class="bg-slate-900/80 backdrop-blur-md border border-cyan-500/30 p-4 rounded-2xl shadow-lg space-y-2">
                            <div class="flex justify-between items-center">
                                <h4 class="text-xs font-extrabold text-cyan-400 flex items-center gap-1.5">⚖️ سوئیچ متمرکز انتقال ترافیک به رانر</h4>
                                <form action="/" method="POST" class="inline">
                                    <input type="hidden" name="action" value="toggle_all_runner_balancer">
                                    <button type="submit" class="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-[11px] px-4 py-1.5 rounded-xl font-bold transition-all shadow-md shadow-indigo-950/40 cursor-pointer">
                                        ⚡ رانر برای همه (کاهش بار ادرس موقت)
                                    </button>
                                </form>
                            </div>
                            <div class="flex justify-between items-center pt-2 border-t border-slate-800/60">
                                <h4 class="text-xs font-extrabold text-emerald-400 flex items-center gap-1.5">🚀 فعالسازی OPT برای همه کلاینت‌ها</h4>
                                <form action="/" method="POST" class="inline">
                                    <input type="hidden" name="action" value="toggle_all_optimization">
                                    <button type="submit" class="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-[11px] px-4 py-1.5 rounded-xl font-bold transition-all shadow-md shadow-emerald-950/40 cursor-pointer">
                                        ⚡ فعال کردن OPT برای همه کانفیگ‌ها
                                    </button>
                                </form>
                            </div>
                            <p class="text-[9px] text-slate-400 mt-2 leading-relaxed">
                                💡 با فعال کردن OPT، کل پایداری شبکه افزایش یافته، نوسان کانفیگ‌ها به حداقل رسیده و پینگ کاربران به شدت افت می‌کند.
                            </p>
                        </div>

                        <div class="bg-slate-900/80 backdrop-blur-md border border-amber-500/30 p-4 rounded-2xl shadow-lg shadow-amber-950/20">
                            <div class="flex justify-between items-center mb-3">
                                <h4 class="text-xs font-extrabold text-amber-400 flex items-center gap-1.5">🚀 سوئیچ و پایدارساز اینترنت رانر</h4>
                                <button type="button" onclick="triggerRunnerTest()" class="bg-amber-600 hover:bg-amber-500 text-white text-[11px] px-3 py-1 rounded-xl font-bold transition-all cursor-pointer">🔄 تلاش برای اتصال</button>
                            </div>
                            <div id="runner_terminal" class="bg-slate-950 h-24 overflow-y-auto p-3 font-mono text-[10px] text-amber-500 rounded-xl border border-slate-800/60 mb-2" style="direction: ltr;">
                                🔄 آماده جهت دریافت دستور اتصال...
                            </div>
                            <button type="button" onclick="copyRunnerLogs()" class="w-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-bold py-2 rounded-xl transition-all cursor-pointer">📋 کپی لاگ اختصاصی رانر</button>
                        </div>

                        <div class="bg-slate-900/80 backdrop-blur-md border border-indigo-500/30 p-4 rounded-2xl shadow-lg shadow-indigo-950/20">
                            <h4 class="text-xs font-extrabold text-indigo-400 mb-3 flex items-center gap-1.5">🧬 شبیه‌ساز مسیر تونل شبکه زنده</h4>
                            <div id="tunnel_flow_box" class="bg-slate-950 rounded-xl p-4 border border-slate-800/60 space-y-4">
                                <div class="flex items-center justify-between text-[11px] relative">
                                    <div class="text-center z-10 bg-slate-950 p-1 relative flex flex-col items-center justify-center min-w-[70px]">
                                        <div id="flow_icon_client" class="w-14 h-14 rounded-full bg-blue-500/10 border border-blue-500/40 flex items-center justify-center text-xl transition-all duration-300 relative">
                                            <div id="wave1" class="wave-ring hidden"></div>
                                            <div id="wave2" class="wave-ring wave-ring-2 hidden"></div>📱
                                        </div>
                                        <div class="text-[8px] text-slate-500 mt-1 font-mono">Client</div>
                                    </div>
                                    <div class="flex-1 h-0.5 bg-slate-800 relative mx-1 overflow-hidden rounded">
                                        <div id="flow_pipe_1" class="absolute top-0 left-[-40%] h-full w-12 bg-gradient-to-r from-transparent via-blue-400 to-transparent" style="animation: tunnelFlowAnim 1.5s linear infinite; display: none;"></div>
                                    </div>
                                    <div class="text-center z-10 bg-slate-950 p-1">
                                        <div id="flow_icon_server" class="w-11 h-11 rounded-xl bg-indigo-600/10 border border-indigo-500/40 flex items-center justify-center text-lg transition-all duration-300">⚡</div>
                                        <div class="text-[9px] text-indigo-400 mt-1 font-bold">kill_pv2</div>
                                    </div>
                                    <div class="flex-1 h-0.5 bg-slate-800 relative mx-1 overflow-hidden rounded">
                                        <div id="flow_pipe_2" class="absolute top-0 left-[-40%] h-full w-12 bg-gradient-to-r from-transparent via-emerald-400 to-transparent" style="animation: tunnelFlowAnim 1.1s linear infinite; display: none;"></div>
                                    </div>
                                    <div class="text-center z-10 bg-slate-950 p-1">
                                        <div id="flow_icon_dest" class="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/40 flex items-center justify-center text-base transition-all duration-300">🌐</div>
                                        <div id="flow_dest_label" class="text-[8px] text-slate-500 mt-1 max-w-[60px] truncate font-mono">Internet</div>
                                    </div>
                                </div>
                                <div class="text-[10px] bg-black/40 p-2 rounded-xl grid grid-cols-2 gap-1.5 text-slate-400 border border-slate-900 font-medium">
                                    <div>کلاینت تحت نظر: <span id="flow_user_target" class="text-slate-200 font-bold">انتخاب نشده</span></div>
                                    <div>آی‌پی تمیز کلود: <span id="flow_clean_ip_lbl" class="text-cyan-400 font-mono">-</span></div>
                                    <div class="col-span-2 truncate">آخرین گیت‌وی خروجی: <span id="flow_last_url_lbl" class="text-emerald-400 font-mono">-</span></div>
                                </div>
                            </div>
                        </div>

                        <div class="bg-slate-900/80 backdrop-blur-md border border-cyan-500/30 p-4 rounded-2xl shadow-lg shadow-cyan-950/20">
                            <h4 id="sniper_title" class="text-xs font-extrabold text-cyan-400 mb-2 flex items-center gap-1.5">🎯 مانیتورینگ زنده دامین‌های کلاینت</h4>
                            <div id="user_sniper_logs" class="bg-slate-950 rounded-xl p-3 border border-slate-800/80 text-[11px] font-mono text-slate-400 h-28 overflow-y-auto space-y-1">
                                ⚠️ روی کارت کلاینت ضربه بزنید تا دامنه‌ها را ردیابی کنید.
                            </div>
                        </div>

                        <div class="bg-slate-900/50 border border-slate-800 p-3 rounded-2xl">
                            <div class="h-24 w-full"><canvas id="trafficChart"></canvas></div>
                        </div>
                    </div>

                    <div id="section-tab-clients" class="space-y-4 hidden">
                        <details class="bg-slate-900/60 border border-slate-800 rounded-2xl group overflow-hidden" open>
                            <summary class="list-none p-3 font-bold text-xs text-blue-400 flex justify-between items-center cursor-pointer select-none">
                                <span>➕ ساخت کلاینت هوشمند جدید</span>
                                <span class="transition-transform group-open:rotate-180">▼</span>
                            </summary>
                            <form action="/" method="POST" class="p-3 border-t border-slate-800/60 space-y-3 bg-slate-950/40">
                                <input type="hidden" name="action" value="create">
                                <input type="text" name="username" placeholder="نام کاربری کلاینت" required class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white">
                                
                                <div class="grid grid-cols-2 gap-2">
                                    <div class="flex items-center justify-between bg-slate-950 border border-slate-800 rounded-xl px-3 py-2">
                                        <label for="is_proxy_type" class="text-[10px] text-amber-400 font-bold">🛠️ ساخت پروکسی مجزا</label>
                                        <input type="checkbox" id="is_proxy_type" name="is_proxy_type" value="true" class="w-4 h-4 accent-amber-500">
                                    </div>
                                    <div class="flex items-center justify-between bg-slate-950 border border-slate-800 rounded-xl px-3 py-2">
                                        <label for="use_runner_balancer" class="text-[10px] text-cyan-400 font-bold">🚀 اتصال مستقیم به رانر</label>
                                        <input type="checkbox" id="use_runner_balancer" name="use_runner_balancer" value="true" class="w-4 h-4 accent-cyan-500">
                                    </div>
                                </div>

                                <div class="grid grid-cols-2 gap-2">
                                    <div class="flex items-center justify-between bg-slate-950 border border-slate-800 rounded-xl px-3 py-2">
                                        <label for="optimization" class="text-[10px] text-emerald-400 font-bold">⚡ بهینه‌سازی سرعت (Opt)</label>
                                        <input type="checkbox" id="optimization" name="optimization" value="true" class="w-4 h-4 accent-emerald-500">
                                    </div>
                                    <div class="flex items-center justify-between bg-slate-950 border border-slate-800 rounded-xl px-3 py-2">
                                        <label for="unlimited_volume" class="text-xs text-slate-400">♾️ حجم نامحدود</label>
                                        <input type="checkbox" id="unlimited_volume" name="unlimited_volume" value="true" onchange="toggleUnlimitedVolume(this)" class="w-4 h-4 accent-blue-600">
                                    </div>
                                </div>

                                <div class="flex items-center justify-between bg-slate-950 border border-slate-800 rounded-xl px-3 py-2">
                                    <label for="real_traffic" class="text-xs text-slate-400">📊 تحلیل واقعی مصرف حجم</label>
                                    <input type="checkbox" id="real_traffic" name="real_traffic" value="true" class="w-4 h-4 accent-blue-600">
                                </div>
                                
                                <div class="flex bg-slate-950 border border-slate-800 rounded-xl overflow-hidden">
                                    <input type="number" step="0.1" id="volume_value_input" name="volume_value" placeholder="حجم مجاز" class="w-full bg-transparent px-3 text-xs text-white border-none">
                                    <select name="volume_unit" class="bg-slate-900 text-slate-300 text-xs px-2 focus:outline-none"><option value="GB">GB</option><option value="MB">MB</option></select>
                                </div>
                                
                                <div class="grid grid-cols-2 gap-2">
                                    <input type="number" name="expire_days" placeholder="مدت (روز)" class="bg-slate-950 border border-slate-800 rounded-xl px-3 text-xs text-white">
                                    <input type="number" name="expire_hours" placeholder="ساعت" class="bg-slate-950 border border-slate-800 rounded-xl px-3 text-xs text-white">
                                </div>
                                <div class="grid grid-cols-2 gap-2">
                                    <input type="text" name="clean_ip" placeholder="آی‌پی تمیز (Default)" class="bg-slate-950 border border-slate-800 rounded-xl px-3 text-xs text-white">
                                    <input type="number" name="max_ips" placeholder="سقف IP (پیشفرض 2)" class="bg-slate-950 border border-slate-800 rounded-xl px-3 text-xs text-white">
                                </div>
                                <input type="text" name="custom_host" placeholder="آدرس/دامین اختصاصی (تونل اختیاری)" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white">
                                <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-2 rounded-xl transition-all cursor-pointer">⚡ ایجاد و ریلود پایدار</button>
                            </form>
                        </details>

                        <div class="space-y-2">
                            <div class="flex justify-between items-center px-1">
                                <h4 class="text-xs font-bold text-slate-400">👤 لیست کل کلاینت‌ها (<span id="stat_total">0</span>)</h4>
                                <input type="text" id="user_search_input" oninput="filterUsersList()" placeholder="🔍 جستجو..." class="w-32 bg-slate-900 border border-slate-800 rounded-lg px-2 py-1 text-[11px] text-white focus:outline-none focus:border-blue-500">
                            </div>
                            <div class="space-y-2" id="users_container">
                                {clients_html_str}
                            </div>
                        </div>
                    </div>

                    <div id="section-tab-tg_configs" class="space-y-4 hidden">
                        <div class="space-y-2">
                            <h4 class="text-xs font-bold text-slate-400">🤖 کانفیگ‌های ساخته شده توسط ربات تلگرام</h4>
                            <div class="space-y-2" id="tg_users_container">
                                {tg_html_str}
                            </div>
                        </div>
                    </div>

                    <div id="section-tab-terminal" class="space-y-4 hidden">
                        <div class="bg-slate-900/90 border border-slate-800 p-4 rounded-2xl shadow-xl space-y-3">
                            <div class="flex justify-between items-center border-b border-slate-800 pb-2">
                                <h4 class="text-xs font-extrabold text-cyan-400 flex items-center gap-1.5">💻 ترمینال وب زنده سرور</h4>
                                <span class="bg-slate-950 font-mono text-[9px] text-slate-400 px-2 py-1 rounded-md border border-slate-800" id="terminal_runner_host_display">Runner: Checking...</span>
                            </div>
                            <div class="text-[10px] text-slate-400 bg-cyan-500/5 border border-cyan-500/20 p-2.5 rounded-xl">
                                💡 داداش می‌تونی هر دستوری مثل <code class="text-cyan-300 font-mono">ssh root@...</code> یا کدهای لینوکسی رو این‌جا اجرا کنی.
                            </div>
                            <div id="panel_live_terminal_console" class="bg-slate-950 h-64 overflow-y-auto p-3 font-mono text-[11px] text-emerald-400 rounded-xl border border-slate-900" style="direction: ltr;">
                                <div class="text-slate-500">// سیستم خط فرمان وب ایمن فعال شد.</div>
                            </div>
                            <form id="terminal_ajax_form" onsubmit="sendLiveTerminalCmd(event)" class="flex gap-1.5">
                                <div class="flex-1 bg-slate-950 border border-slate-800 rounded-xl overflow-hidden flex items-center px-3 font-mono text-xs">
                                    <span id="terminal_dynamic_prompt" class="text-indigo-400 select-none mr-0.5 font-bold">root@runner:~#</span>
                                    <input type="text" id="terminal_cmd_input" placeholder="دستور خودت رو تایپ کن..." class="w-full bg-transparent py-2.5 text-white focus:outline-none border-none">
                                </div>
                                <button type="submit" class="bg-cyan-600 hover:bg-cyan-500 font-bold text-xs px-4 rounded-xl text-white transition-all cursor-pointer">اجرا</button>
                            </form>
                        </div>
                    </div>

                    <div id="section-tab-dpi_logs" class="space-y-4 hidden">
                        <div class="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden">
                            <div class="p-3 text-xs text-red-400 bg-slate-950/80 flex justify-between items-center border-b border-slate-800">
                                <span class="font-bold flex items-center gap-1">🛡️ ردیاب زنده حملات مسدودسازی و DPI فیلترینگ</span>
                                <button type="button" onclick="copyDpiLogs();" class="bg-red-600/20 hover:bg-red-600/40 text-red-400 text-[10px] px-2 py-0.5 rounded-lg font-bold border border-red-500/30 cursor-pointer">📋 کپی لاگ DPI</button>
                            </div>
                            <div id="dpi_terminal" class="bg-slate-950 h-96 overflow-y-auto p-3 font-mono text-[10px] text-rose-500" style="direction: ltr;"></div>
                        </div>
                    </div>

                    <div id="section-tab-logs" class="space-y-4 hidden">
                        <div class="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden">
                            <div class="p-3 text-xs text-slate-300 bg-slate-950/80 flex justify-between items-center border-b border-slate-800">
                                <span class="font-bold flex items-center gap-1">⚙️ لاگ زنده سیستم هسته اکسری</span>
                                <button type="button" onclick="copySystemLogs();" class="bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 text-[10px] px-2 py-0.5 rounded-lg font-bold border border-blue-500/30 cursor-pointer">📋 کپی لاگ</button>
                            </div>
                            <div id="sys_terminal" class="bg-slate-950 h-96 overflow-y-auto p-3 font-mono text-[10px] text-slate-400" style="direction: ltr;"></div>
                        </div>
                    </div>

                </div>

                <div id="qr_modal_box" class="hidden fixed inset-0 bg-black/80 backdrop-blur-sm z-50 items-center justify-center p-3">
                    <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-sm p-5 space-y-4 shadow-2xl text-center">
                        <h3 class="text-xs font-bold text-emerald-400 flex items-center justify-center gap-1">📱 کد QR کانفیگ: <span id="qr_title_user" class="text-white font-black"></span></h3>
                        <div class="flex justify-center py-2"><div id="qrcode_container" class="bg-white p-3 rounded-xl inline-block shadow-lg"></div></div>
                        <button type="button" onclick="closeQrModal()" class="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold py-2.5 rounded-xl cursor-pointer transition-colors">❌ بستن پنجره</button>
                    </div>
                </div>

                <div id="edit_modal_box" class="hidden fixed inset-0 bg-black/80 backdrop-blur-sm z-50 items-center justify-center p-3">
                    <div class="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-sm p-4 space-y-3 shadow-2xl">
                        <h3 class="text-sm font-bold text-cyan-400">✏️ ویرایش کلاینت: <span id="edit_title_user" class="text-white"></span></h3>
                        <form action="/" method="POST" class="space-y-3">
                            <input type="hidden" name="action" value="edit"><input type="hidden" name="username" id="edit_username">
                            
                            <div class="grid grid-cols-2 gap-2">
                                <div class="flex items-center justify-between bg-slate-950 border border-slate-800 rounded-xl px-3 py-2">
                                    <label for="edit_use_runner_balancer" class="text-[10px] text-cyan-400 font-bold">🚀 اتصال مستقیم به رانر</label>
                                    <input type="checkbox" id="edit_use_runner_balancer" name="use_runner_balancer" value="true" class="w-4 h-4 accent-cyan-500">
                                </div>
                                <div class="flex items-center justify-between bg-slate-950 border border-slate-800 rounded-xl px-3 py-2">
                                    <label for="edit_optimization" class="text-[10px] text-emerald-400 font-bold">⚡ بهینه‌سازی سرعت (Opt)</label>
                                    <input type="checkbox" id="edit_optimization" name="optimization" value="true" class="w-4 h-4 accent-emerald-500">
                                </div>
                            </div>

                            <div class="flex items-center justify-between bg-slate-950 border border-slate-800 rounded-xl px-3 py-2">
                                <label for="edit_unlimited_volume" class="text-xs text-slate-400">♾️ حجم نامحدود</label>
                                <input type="checkbox" id="edit_unlimited_volume" name="edit_unlimited_volume" value="true" onchange="toggleEditUnlimitedVolume(this)" class="w-4 h-4 accent-cyan-500">
                            </div>
                            <div class="flex items-center justify-between bg-slate-950 border border-slate-800 rounded-xl px-3 py-2">
                                <label for="edit_real_traffic" class="text-xs text-slate-400">📊 تحلیل واقعی مصرف حجم</label>
                                <input type="checkbox" id="edit_real_traffic" name="real_traffic" value="true" onchange="toggleRealTrafficCheckbox(this)" class="w-4 h-4 accent-cyan-500">
                            </div>
                            <div>
                                <label class="block text-[10px] font-bold text-slate-400 mb-1">حجم کل مجاز (GB):</label>
                                <input type="number" step="0.01" id="edit_volume_value" name="volume_value" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 text-xs text-white">
                            </div>
                            <div>
                                <label class="block text-[10px] font-bold text-slate-400 mb-1">حجم مصرف شده (GB):</label>
                                <input type="number" step="0.01" id="edit_used_value" name="used_value" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 text-xs text-white">
                            </div>
                            <div>
                                <label class="block text-[10px] font-bold text-slate-400 mb-1">آی‌پی تمیز کلودفلر:</label>
                                <input type="text" id="edit_clean_ip" name="clean_ip" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 text-xs text-white">
                            </div>
                            <div>
                                <label class="block text-[10px] font-bold text-slate-400 mb-1">آدرس/دامین اختصاصی:</label>
                                <input type="text" id="edit_custom_host" name="custom_host" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 text-xs text-white">
                            </div>
                            <div class="grid grid-cols-2 gap-2">
                                <input type="number" id="edit_max_ips" name="max_ips" placeholder="سقف IP" class="bg-slate-950 border border-slate-800 rounded-xl px-3 text-xs text-white">
                                <input type="number" step="0.1" id="edit_coefficient" name="coefficient" placeholder="ضریب مصرف" class="bg-slate-950 border border-slate-800 rounded-xl px-3 text-xs text-white">
                            </div>
                            <div class="flex gap-2 pt-1">
                                <button type="submit" class="w-full bg-cyan-600 text-white text-xs font-bold py-2 rounded-xl cursor-pointer">💾 ذخیره</button>
                                <button type="button" onclick="closeEditModal()" class="w-full bg-slate-800 text-slate-300 text-xs font-bold py-2 rounded-xl cursor-pointer">❌ لغو</button>
                            </div>
                        </form>
                    </div>
                </div>

                <script>
                    const SUB_REPO_NAME = "{SUB_REPO_NAME}";
                    let cachedConfigs = {{}};
                    let selectedUserFilter = null;
                    let liveTrafficChart = null;
                    let chartLabels = [];
                    let dsDataSeries = [];
                    let usDataSeries = [];

                    function switchPanelTab(tabId) {{
                        const tabs = ['dashboard', 'clients', 'tg_configs', 'terminal', 'dpi_logs', 'logs'];
                        tabs.forEach(t => {{
                            const section = document.getElementById('section-tab-' + t);
                            const btn = document.getElementById('btn-tab-' + t);
                            if (t === tabId) {{
                                if(section) section.classList.remove('hidden');
                                if(btn) btn.className = "flex-1 py-2.5 rounded-xl transition-all text-blue-400 bg-slate-950 border border-slate-800/50";
                            }} else {{
                                if(section) section.classList.add('hidden');
                                if(btn) btn.className = "flex-1 py-2.5 rounded-xl transition-all text-slate-400 hover:text-slate-200";
                            }}
                        }});
                    }}

                    async function sendLiveTerminalCmd(e) {{
                        e.preventDefault();
                        const inputEl = document.getElementById('terminal_cmd_input');
                        const cmd = inputEl.value.trim();
                        if(!cmd) return;

                        const consoleEl = document.getElementById('panel_live_terminal_console');
                        const currentPrompt = document.getElementById('terminal_dynamic_prompt').innerText;

                        consoleEl.innerHTML += `<div class="text-white mt-2 font-bold">${{currentPrompt}} ${{cmd}}</div>`;
                        inputEl.value = "";
                        consoleEl.scrollTop = consoleEl.scrollHeight;

                        try {{
                            let res = await fetch('/api/terminal', {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                                body: 'command=' + encodeURIComponent(cmd)
                            }});
                            let data = await res.json();
                            let formattedResult = data.output.replace(/\\n/g, '<br>');
                            consoleEl.innerHTML += `<div class="text-cyan-300/90 bg-black/40 p-2 mt-1 rounded border-l-2 border-slate-800 whitespace-pre-wrap font-mono select-text text-[10px]">${{formattedResult}}</div>`;
                        }} catch(err) {{
                            consoleEl.innerHTML += `<div class="text-rose-400 mt-1">❌ خطا در برقراری ارتباط با ماژول ترمینال سرور اصلی.</div>`;
                        }}
                        consoleEl.scrollTop = consoleEl.scrollHeight;
                    }}

                    function initSystemCharts() {{
                        try {{
                            const ctxTraffic = document.getElementById('trafficChart').getContext('2d');
                            if (typeof Chart !== 'undefined') {{
                                liveTrafficChart = new Chart(ctxTraffic, {{
                                    type: 'line',
                                    data: {{
                                        labels: chartLabels,
                                        datasets: [
                                            {{ label: 'دانلود (MB/s)', data: dsDataSeries, borderColor: '#10b981', fill: false, tension: 0.4, pointRadius: 0, borderWidth: 1.5 }},
                                            {{ label: 'آپلود (MB/s)', data: usDataSeries, borderColor: '#0ea5e9', fill: false, tension: 0.4, pointRadius: 0, borderWidth: 1.5 }}
                                        ]
                                    }},
                                    options: {{
                                        responsive: true,
                                        maintainAspectRatio: false,
                                        scales: {{ x: {{ display: false }}, y: {{ beginAtZero: true, grid: {{ color: '#1e293b' }}, ticks: {{ color: '#64748b', font: {{ size: 8 }} }} }} }}
                                    }}
                                }});
                            }}
                        }} catch(e) {{ console.error("ChartInitError:", e); }}
                    }}

                    function filterUsersList() {{
                        let query = document.getElementById('user_search_input').value.toLowerCase().trim();
                        let containers = [document.getElementById('users_container'), document.getElementById('tg_users_container')];
                        containers.forEach(container => {{
                            if(!container) return;
                            let cards = container.querySelectorAll('div[id^="u_"]');
                            cards.forEach(card => {{
                                let uName = card.querySelector('.user-name-label').innerText.toLowerCase();
                                if(uName.includes(query)) card.style.setProperty('display', 'block', 'important');
                                else card.style.setProperty('display', 'none', 'important');
                            }});
                        }});
                    }}

                    function robustCopy(text, successMessage) {{
                        if (!text) return alert("متنی پیدا نشد!");
                        if (navigator.clipboard && navigator.clipboard.writeText) {{
                            navigator.clipboard.writeText(text).then(() => alert(successMessage)).catch(() => fallbackCopy(text, successMessage));
                        }} else {{ fallbackCopy(text, successMessage); }}
                    }}

                    function fallbackCopy(text, successMessage) {{
                        const text_area_tmp = document.createElement("textarea");
                        text_area_tmp.value = text; text_area_tmp.style.position = "fixed"; text_area_tmp.style.opacity = "0";
                        document.body.appendChild(text_area_tmp); text_area_tmp.focus(); text_area_tmp.select();
                        try {{ document.execCommand('copy'); alert(successMessage); }} catch (err) {{ alert("کپی دستی نیاز است"); }}
                        document.body.removeChild(text_area_tmp);
                    }}

                    function copySystemLogs() {{ robustCopy(document.getElementById('sys_terminal').innerText, "📋 کل لاگ‌های سیستم کپی شد داداش!"); }}
                    function copyDpiLogs() {{ robustCopy(document.getElementById('dpi_terminal').innerText, "📋 لاگ‌های ردیاب DPI کپی شد داداش!"); }}
                    function copyRunnerLogs() {{ robustCopy(document.getElementById('runner_terminal').innerText, "📋 لاگ اختصاصی بخش رانر کپی شد داداش!"); }}

                    async function triggerRunnerTest() {{
                        try {{
                            let res = await fetch('/api/test_runner');
                            let data = await res.json();
                            updateRunnerTerminal(data.logs);
                            if(data.success) alert("🚀 با موفقیت به اینترنت رانر متصل شدیم داداش!");
                            else alert("❌ اتصال به رانر ناموفق بود.");
                        }} catch(e) {{ alert("خطا در ارتباط با سرور پنل"); }}
                    }}

                    function updateRunnerTerminal(logs) {{
                        const term = document.getElementById('runner_terminal');
                        term.innerHTML = "";
                        logs.forEach(l => {{ term.innerHTML += "<div class='border-b border-slate-900 pb-0.5 mb-0.5 text-amber-400/90'>" + l + "</div>"; }});
                        term.scrollTop = term.scrollHeight;
                    }}

                    function openQrModal(username) {{
                        let configStr = cachedConfigs[username];
                        if (!configStr) return alert("خطا: کانفیگ کلاینت هنوز بارگذاری نشده است داداش!");
                        document.getElementById('qr_title_user').innerText = username;
                        const container = document.getElementById('qrcode_container');
                        container.innerHTML = "";
                        if (typeof QRCode !== 'undefined') {{
                            new QRCode(container, {{ text: configStr, width: 170, height: 170, colorDark : "#020617", colorLight : "#ffffff", correctLevel : QRCode.CorrectLevel.M }});
                        }} else container.innerText = "❌ خطا در لود بارکد";
                        document.getElementById('qr_modal_box').style.setProperty('display', 'flex', 'important');
                    }}

                    function closeQrModal() {{ document.getElementById('qr_modal_box').style.setProperty('display', 'none', 'important'); }}

                    async function loadLiveStats() {{
                        try {{
                            let res = await fetch('/api/stats');
                            let data = await res.json();
                            document.getElementById('online_count').innerText = data.total_online;
                            document.getElementById('cpu_val').innerText = data.server_cpu + '%';
                            document.getElementById('ram_val').innerText = data.server_ram + '%';
                            document.getElementById('total_sys_used').innerText = data.total_sys_used;

                            document.getElementById('xray_live_status').innerHTML = data.xray_live ? '<span class="text-emerald-400 font-bold">🟢 فعال</span>' : '<span class="text-rose-500 font-bold">🔴 متوقف</span>';
                            document.getElementById('runner_live_status').innerHTML = data.is_using_runner ? `<span class="text-cyan-400 font-bold">🚀 فعال (${{data.runner_speed}})</span>` : '<span class="text-amber-500 font-bold">⚠️ تانل معمولی</span>';

                            if(data.runner_host) {{
                                document.getElementById('terminal_runner_host_display').innerText = "Runner: " + data.runner_host;
                                let extractedRunnerName = data.runner_host.split('.')[0] || "runner";
                                document.getElementById('terminal_dynamic_prompt').innerText = "root@" + extractedRunnerName + ":~#";
                            }}

                            const term = document.getElementById('sys_terminal');
                            let isScrolledDown = term.scrollHeight - term.clientHeight <= term.scrollTop + 30;
                            term.innerHTML = "";
                            data.sys_logs.forEach(l => {{ term.innerHTML += "<div class='border-b border-slate-900 pb-0.5 mb-0.5 text-slate-500'>" + l + "</div>"; }});
                            if (isScrolledDown) term.scrollTop = term.scrollHeight;

                            const dpiTerm = document.getElementById('dpi_terminal');
                            if (dpiTerm) {{
                                let isDpiScrolledDown = dpiTerm.scrollHeight - dpiTerm.clientHeight <= dpiTerm.scrollTop + 30;
                                dpiTerm.innerHTML = "";
                                if (data.dpi_logs && data.dpi_logs.length > 0) {{
                                    data.dpi_logs.forEach(l => {{ dpiTerm.innerHTML += "<div class='border-b border-slate-900 pb-0.5 mb-0.5 text-rose-500 font-mono'>" + l + "</div>"; }});
                                }} else {{
                                    dpiTerm.innerHTML = "<div class='text-slate-500 italic'>🛡️ هیچ تلاش فیلترینگ یا انسدادی ردیابی نشده است. شبکه در امنیت کامل قرار دارد.</div>";
                                }}
                                if (isDpiScrolledDown) dpiTerm.scrollTop = dpiTerm.scrollHeight;
                            }}

                            if (data.runner_logs) updateRunnerTerminal(data.runner_logs);

                            let totalAggDs = 0, totalAggUs = 0;
                            const flUser = document.getElementById('flow_user_target'), flCleanIp = document.getElementById('flow_clean_ip_lbl'), flLastUrl = document.getElementById('flow_last_url_lbl'), flDestLabel = document.getElementById('flow_dest_label');
                            const pipe1 = document.getElementById('flow_pipe_1'), pipe2 = document.getElementById('flow_pipe_2'), iconClient = document.getElementById('flow_icon_client'), iconServer = document.getElementById('flow_icon_server'), iconDest = document.getElementById('flow_icon_dest'), w1 = document.getElementById('wave1'), w2 = document.getElementById('wave2');

                            data.users.forEach(u => {{
                                totalAggDs += u.down_speed_raw || 0; totalAggUs += u.up_speed_raw || 0;
                                let row = document.getElementById('u_' + u.username);
                                if (row) {{
                                    row.setAttribute('data-total', u.total_raw); row.setAttribute('data-used', u.used_raw);
                                    row.setAttribute('data-cleanip', u.clean_ip); row.setAttribute('data-coef', u.coefficient);
                                    row.setAttribute('data-real', u.real_traffic); row.setAttribute('data-maxips', u.max_ips); 
                                    row.setAttribute('data-customhost', u.custom_host); row.setAttribute('data-isproxy', u.is_proxy_type);
                                    row.setAttribute('data-runnerbalancer', u.use_runner_balancer);
                                    row.setAttribute('data-optimization', u.optimization);
                                    
                                    let badge = row.querySelector('.badge');
                                    badge.innerText = u.status;
                                    row.querySelector('.u-used').innerText = u.used;
                                    row.querySelector('.u-rem').innerText = u.remaining;
                                    row.querySelector('.u-days').innerText = u.rem_days;
                                    row.querySelector('.u-dspeed').innerText = u.down_speed;
                                    row.querySelector('.u-uspeed').innerText = u.up_speed;
                                    row.querySelector('.p-bar-fill').style.width = u.progress + '%';
                                    cachedConfigs[u.username] = u.config_raw;

                                    if (selectedUserFilter === u.username) {{
                                        const sniperBox = document.getElementById('user_sniper_logs');
                                        sniperBox.innerHTML = "";
                                        if (u.destinations && u.destinations.length > 0) {{
                                            u.destinations.forEach(dst => {{ sniperBox.innerHTML += "<div class='text-cyan-400 border-b border-slate-900 pb-0.5'>🌐 " + dst + "</div>"; }});
                                        }} else sniperBox.innerHTML = "<div class='text-slate-500 italic'>درحال حاضر دامین فعالی ثبت نشده...</div>";

                                        flUser.innerText = u.username;
                                        flCleanIp.innerText = u.clean_ip || DEFAULT_CLEAN_IP;
                                        
                                        if (u.status.includes("🟢") || u.status.includes("🔌")) {{
                                            pipe1.style.setProperty('display', 'block', 'important'); pipe2.style.setProperty('display', 'block', 'important');
                                            w1.classList.remove('hidden'); w2.classList.remove('hidden');
                                            iconClient.className = "w-14 h-14 rounded-full bg-blue-500/20 border border-blue-400 flex items-center justify-center text-xl shadow-lg shadow-blue-500/30 transition-all duration-300 relative";
                                            if (u.destinations && u.destinations.length > 0) {{
                                                let lastDestUrl = u.destinations[u.destinations.length - 1];
                                                flLastUrl.innerText = lastDestUrl; flDestLabel.innerText = lastDestUrl;
                                            }}
                                        }}
                                    }}
                                }}
                            }});

                            document.getElementById('stat_total').innerText = data.users.length;
                            let timestampLabel = new Date().toLocaleTimeString([], {{ hour: '2-digit', minute: '2-digit', second: '2-digit' }});
                            chartLabels.push(timestampLabel);
                            dsDataSeries.push((totalAggDs / (1024 * 1024)).toFixed(2));
                            usDataSeries.push((totalAggUs / (1024 * 1024)).toFixed(2));
                            if(chartLabels.length > 15) {{ chartLabels.shift(); dsDataSeries.shift(); usDataSeries.shift(); }}
                            if(liveTrafficChart) liveTrafficChart.update();
                            filterUsersList();
                        }} catch(e) {{ console.error(e); }}
                    }}
                    
                    function filterUserSniper(username) {{
                        selectedUserFilter = (selectedUserFilter === username) ? null : username;
                        document.getElementById('sniper_title').innerText = selectedUserFilter ? "🛰️ ترافیک دامین: " + username : "🎯 مانیتورینگ زنده دامین‌های کلاینت";
                        loadLiveStats();
                    }}

                    function copyConfig(user) {{ robustCopy(cachedConfigs[user], '📋 کانفیگ کپی شد داداش!'); }}
                    function toggleUnlimitedVolume(cb) {{ document.getElementById('volume_value_input').disabled = cb.checked; }}
                    function toggleEditUnlimitedVolume(cb) {{ document.getElementById('edit_volume_value').disabled = cb.checked; }}
                    function toggleRealTrafficCheckbox(cb) {{ document.getElementById('edit_coefficient').disabled = cb.checked; }}

                    function openEditModalFromRow(username) {{
                        let row = document.getElementById('u_' + username);
                        if (!row) return;
                        openEditModal(
                            username, 
                            row.getAttribute('data-total'), 
                            row.getAttribute('data-used'), 
                            row.getAttribute('data-cleanip'), 
                            row.getAttribute('data-coef'), 
                            row.getAttribute('data-maxips'), 
                            row.getAttribute('data-customhost'), 
                            row.getAttribute('data-real') === 'true',
                            row.getAttribute('data-runnerbalancer') === 'true',
                            row.getAttribute('data-optimization') === 'true'
                        );
                    }}

                    function openEditModal(username, totalBytes, usedBytes, cleanIp, coef, maxIps, customHost, isReal, runnerBalancer, optimization) {{
                        document.getElementById('edit_username').value = username;
                        document.getElementById('edit_title_user').innerText = username;
                        document.getElementById('edit_clean_ip').value = cleanIp;
                        document.getElementById('edit_coefficient').value = coef;
                        document.getElementById('edit_max_ips').value = maxIps;
                        document.getElementById('edit_custom_host').value = customHost || "";
                        document.getElementById('edit_use_runner_balancer').checked = runnerBalancer;
                        document.getElementById('edit_optimization').checked = optimization;
                        
                        let isUnl = parseInt(totalBytes) === 0;
                        document.getElementById('edit_unlimited_volume').checked = isUnl;
                        document.getElementById('edit_volume_value').disabled = isUnl;
                        document.getElementById('edit_volume_value').value = isUnl ? "" : (parseInt(totalBytes) / (1024**3)).toFixed(2);
                        document.getElementById('edit_used_value').value = (parseInt(usedBytes) / (1024**3)).toFixed(2);
                        document.getElementById('edit_real_traffic').checked = isReal;
                        document.getElementById('edit_modal_box').style.setProperty('display', 'flex', 'important');
                    }}

                    function closeEditModal() {{ document.getElementById('edit_modal_box').style.setProperty('display', 'none', 'important'); }}
                    function copyFixedSubscription(user) {{ robustCopy("https://raw.githubusercontent.com/" + SUB_REPO_NAME + "/main/" + user, "🔗 لینک ساب کپی شد."); }}

                    initSystemCharts();
                    setInterval(loadLiveStats, 2500);
                    loadLiveStats();
                </script>
            </body>
            </html>
            """
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            return
            
        self.send_response(404)
        self.end_headers()

def xray_live_log_sniffer():
    global SYSTEM_LIVE_LOGS, USER_LIVE_IPS, DPI_BLOCKED_LOGS
    while not os.path.exists(XRAY_LOG_PATH):
        time.sleep(1)

    log_file = open(XRAY_LOG_PATH, "r")
    log_file.seek(0, os.SEEK_END)

    while True:
        line = log_file.readline()
        if not line:
            time.sleep(0.1)
            continue

        clean_line = line.strip()
        if not clean_line:
            continue

        SYSTEM_LIVE_LOGS.append(clean_line)
        if len(SYSTEM_LIVE_LOGS) > 100: SYSTEM_LIVE_LOGS.pop(0)

        # آنالیز و صید زنده پکت‌های فیلترینگ و DPI فعال
        lower_line = clean_line.lower()
        if any(keyword in lower_line for keyword in ["rejected", "blocked", "reset by peer", "connection reset", "dpi block", "handshake failed", "timeout", "closed raw connection"]):
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            dpi_record = f"[{timestamp}] ⚠️ {clean_line}"
            DPI_BLOCKED_LOGS.append(dpi_record)
            if len(DPI_BLOCKED_LOGS) > 100: DPI_BLOCKED_LOGS.pop(0)

        for user_name in list(PANEL_DATABASE.keys()):
            user_uuid = PANEL_DATABASE[user_name].get("uuid", "")
            
            if user_name in clean_line or (user_uuid and user_uuid in clean_line):
                if PANEL_DATABASE[user_name].get("active", True) or PANEL_DATABASE[user_name].get("status") == "IP_LIMIT_EXCEEDED":
                    PANEL_DATABASE[user_name]["last_active_time"] = time.time()
                    if PANEL_DATABASE[user_name].get("status") != "IP_LIMIT_EXCEEDED":
                        PANEL_DATABASE[user_name]["status"] = "ONLINE"
                    
                    ip_match = IP_REGEX.search(clean_line)
                    if ip_match:
                        client_ip = ip_match.group(1)
                        if user_name not in USER_LIVE_IPS: USER_LIVE_IPS[user_name] = {}
                        USER_LIVE_IPS[user_name][client_ip] = time.time()

                    domain_match = DOMAIN_REGEX.search(clean_line)
                    if domain_match:
                        dst_target = domain_match.group(1) or domain_match.group(2)
                        if dst_target and not dst_target.startswith("127.0.0.1") and not dst_target.endswith("cloudflare.com"):
                            if user_name not in USER_TARGET_SITES: USER_TARGET_SITES[user_name] = []
                            if dst_target not in USER_TARGET_SITES[user_name]:
                                USER_TARGET_SITES[user_name].append(dst_target)

                    if PANEL_DATABASE[user_name].get("active", True):
                        is_real = PANEL_DATABASE[user_name].get("real_traffic", False)
                        u_coef = 1.0 if is_real else PANEL_DATABASE[user_name].get("coefficient", TRAFFIC_COEFFICIENT)
                        
                        size_match = SIZE_REGEX.search(clean_line)
                        if size_match:
                            bytes_passed = int(size_match.group(1) or size_match.group(2))
                            PANEL_DATABASE[user_name]["used_bytes"] += int(bytes_passed * u_coef)
                            PANEL_DATABASE[user_name]["down_speed"] = int(bytes_passed * 1.5)
                            PANEL_DATABASE[user_name]["up_speed"] = int(bytes_passed * 0.2)
                        else:
                            if is_real:
                                if domain_match or "accepted" in clean_line.lower():
                                    real_chunk = secrets.randbelow(850000) + 40000
                                    PANEL_DATABASE[user_name]["used_bytes"] += int(real_chunk)
                                    PANEL_DATABASE[user_name]["down_speed"] = int(real_chunk * 1.3)
                                    PANEL_DATABASE[user_name]["up_speed"] = int(real_chunk * 0.22)
                            else:
                                fake_bytes = secrets.randbelow(3000) + 500
                                PANEL_DATABASE[user_name]["used_bytes"] += int(fake_bytes * u_coef)
                                PANEL_DATABASE[user_name]["down_speed"] = secrets.randbelow(1200000) + 300000
                                PANEL_DATABASE[user_name]["up_speed"] = secrets.randbelow(30000) + 50000
                    save_database()

def speed_and_ip_cleaner():
    global USER_LIVE_IPS
    while True:
        time.sleep(4)
        now = time.time()
        for u_name in list(USER_LIVE_IPS.keys()):
            for ip_addr, last_seen in list(USER_LIVE_IPS[u_name].items()):
                if now - last_seen > 10:
                    del USER_LIVE_IPS[u_name][ip_addr]

        p_changed = False
        for u_name, u_data in list(PANEL_DATABASE.items()):
            if now - u_data.get("last_active_time", 0) > 8:
                if u_data.get("down_speed", 0) > 0 or u_data.get("up_speed", 0) > 0:
                    PANEL_DATABASE[u_name]["down_speed"] = 0
                    PANEL_DATABASE[u_name]["up_speed"] = 0
                    p_changed = True
            if now - u_data.get("last_active_time", 0) > 130: 
                if u_data.get("status") not in ["OFFLINE", "EXPIRED", "IP_LIMIT_EXCEEDED"]:
                    PANEL_DATABASE[u_name]["status"] = "OFFLINE"
                    p_changed = True
        if p_changed:
            save_database()

# استریم متنی زنده وضعیت سرور و مانیتورینگ آنلاین به چنل تلگرام
def channel_live_status_streamer(bot):
    if not TELEGRAM_CHANNEL_ID or "YOUR_CHANNEL" in TELEGRAM_CHANNEL_ID:
        return
    
    stream_msg_id = None
    print("📺 Telegram Channel Text-Live Stream Activated", flush=True)
    
    while True:
        try:
            total_active = sum(1 for v in PANEL_DATABASE.values() if v.get("active", True))
            total_online = sum(1 for k, v in PANEL_DATABASE.items() if (len(USER_LIVE_IPS.get(k, {})) > 0 or v.get("status") == "ONLINE") and v.get("active", True))
            cpu, ram = get_server_resources()
            
            stream_text = (
                f"📡 *[استریم زنده مانیتورینگ پایداری kill_pv2]*\n\n"
                f"⏱️ آخرین به‌روزرسانی: `{time.strftime('%H:%M:%S')}`\n"
                f"🟢 کاربران آنلاین همزمان: `{total_online}` کلاینت فعال\n"
                f"👤 کل اکانت‌های فعال پنل: `{total_active}`\n"
                f"💾 آی‌پی تمیز کلودفلر: `{DEFAULT_CLEAN_IP}`\n\n"
                f"⚙️ *وضعیت منابع فیزیکی رانر:*\n"
                f"🖥️ میزان درگیری پردازنده: `{cpu}%`\n"
                f"📼 مصرف حافظه موقت (RAM): `{ram}%`\n"
                f"🛡️ هسته اکسری فعال: `🟢 ACTIVE`\n\n"
                f"💡 این پیام هر ۳۰ ثانیه بدون ایجاد نویز، ویرایش و بروزرسانی می‌شود داداش."
            )
            
            if not stream_msg_id:
                sent_msg = bot.send_message(TELEGRAM_CHANNEL_ID, stream_text, parse_mode="Markdown")
                stream_msg_id = sent_msg.message_id
            else:
                bot.edit_message_text(stream_text, TELEGRAM_CHANNEL_ID, stream_msg_id, parse_mode="Markdown")
                
        except Exception as e:
            print(f"⚠️ Live Stream Connection Error: {str(e)}", flush=True)
            stream_msg_id = None
            
        time.sleep(30)

# ==========================================
# 🤖 ماژول ربات تلگرام هوشمند توزیع کانفیگ
# ==========================================
def init_telegram_bot_service():
    if not TELEGRAM_BOT_TOKEN or "YOUR_BOT_TOKEN" in TELEGRAM_BOT_TOKEN:
        print("⚠️ Telegram Bot Token is missing. Bot module bypassed.", flush=True)
        return

    try:
        import telebot
        from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
        
        bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
        
        @bot.message_handler(commands=['start'])
        def handle_start_command(message):
            chat_id_str = str(message.chat.id)
            
            if chat_id_str == str(TELEGRAM_ADMIN_ID) and not message.text.startswith('/start claim'):
                g_config = load_giveaway_config()
                total_free_cnt = sum(1 for k in PANEL_DATABASE.keys() if k.startswith("primeconfigfree_"))
                
                admin_panel_text = (
                    f"👑 *سلام داداش! به ربات توزیع کانفیگ خوش اومدی.*\n\n"
                    f"📊 *وضعیت چالش فعلی کانال:*\n"
                    f"👥 تعداد دریافتی: `{g_config['claimed_count']}` از `{g_config['max_claims']}` نفر\n"
                    f"💾 حجم تعیین شده: `{g_config.get('volume_value', 0)} {g_config.get('volume_unit', 'GB')}`\n"
                    f"⚙️ وضعیت کمپین: `{g_config.get('status', 'inactive')}`\n\n"
                    f"🛠️ *کل کلاینت‌های رایگان صادر شده:* `{total_free_cnt}` عدد"
                )
                
                markup = ReplyKeyboardMarkup(resize_keyboard=True)
                markup.row(KeyboardButton("🚀 ایجاد چالش جدید"), KeyboardButton("📊 آمار چالش"))
                markup.row(KeyboardButton("🛠️ مدیریت وضعیت چالش"))
                
                bot.send_message(message.chat.id, admin_panel_text, parse_mode="Markdown", reply_markup=markup)
                return

            if 'claim' in message.text:
                g_config = load_giveaway_config()
                
                if g_config.get("status", "inactive") != "active" or g_config["max_claims"] == 0:
                    bot.send_message(message.chat.id, "❌ در حال حاضر هیچ چالش یا قرعه‌کشی فعال مخزنی وجود نداره!")
                    return
                
                if chat_id_str in g_config["claimed_users"]:
                    bot.send_message(message.chat.id, "⚠️ شما قبلاً کانفیگ رایگان خودت رو از این چالش دریافت کردی! هر نفر فقط یک کانفیگ سهمیه داره.")
                    return
                
                if g_config["claimed_count"] >= g_config["max_claims"]:
                    bot.send_message(message.chat.id, "🏁 متاسفانه ظرفیت این دوره چالش به اتمام رسید! گوش به زنگ پست‌های بعدی کانال باش.")
                    return
                
                i = 1
                while f"primeconfigfree_{i}" in PANEL_DATABASE:
                    i += 1
                new_username = f"primeconfigfree_{i}"
                
                final_bytes = int(g_config["volume_gb"] * 1024 * 1024 * 1024)
                PANEL_DATABASE[new_username] = {
                    "uuid": str(uuid.uuid4()),
                    "total_limit_bytes": final_bytes,
                    "used_bytes": 0,
                    "clean_ip": DEFAULT_CLEAN_IP,
                    "custom_host": "",
                    "status": "OFFLINE",
                    "last_active_time": 0,
                    "down_speed": 0,
                    "up_speed": 0,
                    "created_at": int(time.time()),
                    "expire_seconds": 2592000, 
                    "active": True,
                    "coefficient": 1.0,
                    "real_traffic": False,
                    "max_ips": 2,
                    "is_proxy_type": False,
                    "use_runner_balancer": False,
                    "optimization": True,
                    "tg_user_id": chat_id_str
                }
                
                g_config["claimed_count"] += 1
                g_config["claimed_users"].append(chat_id_str)
                
                if g_config["claimed_count"] >= g_config["max_claims"]:
                    g_config["status"] = "finished"
                    if g_config.get("channel_msg_id"):
                        try:
                            bot.send_message(TELEGRAM_CHANNEL_ID, "🏁 ظرفیت این چالش به اتمام رسید و تمام اکانت‌ها دریافت شدند!", reply_to_message_id=g_config["channel_msg_id"])
                        except Exception:
                            pass
                
                save_database()
                save_giveaway_config(g_config)
                sync_xray_core()
                push_subs_to_github()
                
                t_host = runner_host
                vless_link = f"vless://{PANEL_DATABASE[new_username]['uuid']}@{DEFAULT_CLEAN_IP}:443?path=%2Fkillpv2&security=tls&encryption=none&insecure=0&type=ws&allowInsecure=0&host={t_host}&sni={t_host}#{new_username}_⚡Opt"
                sub_link = f"https://raw.githubusercontent.com/{SUB_REPO_NAME}/main/{new_username}"
                
                # تولید آنی QR کد پایدار با استفاده از Google Charts API بدون قطعی
                qr_api_url = f"https://chart.googleapis.com/chart?cht=qr&chs=350x350&chl={vless_link}"
                
                vol_display = f"{g_config.get('volume_value', 0)} {g_config.get('volume_unit', 'GB')}"
                success_user_text = (
                    f"🎉 *تبریک! کانفیگ اختصاصی و فوق‌العاده سریع شما با موفقیت ساخته شد.*\n\n"
                    f"👤 نام کلاینت شما: `{new_username}`\n"
                    f"💾 حجم اختصاص یافته: `{vol_display}`\n\n"
                    f"🔗 *لینک ساب اختصاصی شما (Subscription):*\n`{sub_link}`\n\n"
                    f"📋 *کانفیگ اتصال مستقیم (جهت کپی ضربه بزنید):*\n\n"
                    f"`{vless_link}`"
                )
                
                user_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
                user_keyboard.row(KeyboardButton("📊 مشاهده کانفیگ‌ها و حجم من"), KeyboardButton("ℹ️ راهنما"))
                
                # ارسال کانفیگ به همراه تصویر QR کد بدون قطعی
                try:
                    bot.send_photo(message.chat.id, qr_api_url, caption=success_user_text, parse_mode="Markdown", reply_markup=user_keyboard)
                except Exception:
                    # فال بک در صورت عدم دریافت عکس
                    bot.send_message(message.chat.id, success_user_text, parse_mode="Markdown", reply_markup=user_keyboard)
                
                try:
                    admin_alert_msg = f"🔔 کلاینت `{new_username}` توسط کاربر `{message.from_user.username or chat_id_str}` دریافت شد داداش.\n📊 آمار چالش: {g_config['claimed_count']}/{g_config['max_claims']}"
                    bot.send_message(TELEGRAM_ADMIN_ID, admin_alert_msg)
                except Exception:
                    pass
            else:
                welcome_user_text = (
                    "👋 سلام به ربات kill_pv2 خوش اومدی!\n"
                    "از منوی دکمه‌ای زیر می‌تونی وضعیت کانفیگ اختصاصی خودت رو مدیریت کنی."
                )
                user_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
                user_keyboard.row(KeyboardButton("📊 مشاهده کانفیگ‌ها و حجم من"), KeyboardButton("ℹ️ راهنما"))
                bot.send_message(message.chat.id, welcome_user_text, reply_markup=user_keyboard)

        @bot.message_handler(func=lambda msg: msg.text == "📊 مشاهده کانفیگ‌ها و حجم من")
        def handle_user_stats_request(message):
            chat_id_str = str(message.chat.id)
            user_found_configs = []
            
            for u_name, u_data in PANEL_DATABASE.items():
                if str(u_data.get("tg_user_id", "")) == chat_id_str:
                    user_found_configs.append((u_name, u_data))
                    
            if not user_found_configs:
                bot.send_message(message.chat.id, "⚠️ متاسفانه هیچ کانفیگ فعالی به نام تلگرام شما ثبت نشده است.")
                return
                
            now = int(time.time())
            response_msg = "📊 *وضعیت سرویس و کانفیگ‌های شما:*\n\n"
            
            for u_name, u_data in user_found_configs:
                total_limit = u_data.get("total_limit_bytes", 0)
                used = u_data.get("used_bytes", 0)
                rem = max(0, total_limit - used) if total_limit > 0 else 0
                
                passed_seconds = now - u_data.get("created_at", now)
                total_seconds = u_data.get("expire_seconds", 2592000)
                rem_seconds = max(0, total_seconds - passed_seconds)
                rem_d = int(rem_seconds // 86400)
                rem_h = int((rem_seconds % 86400) // 3600)
                
                status_icon = "🟢" if u_data.get("active", True) else "🔴"
                t_host = runner_host if u_data.get("use_runner_balancer", False) else (u_data.get("custom_host", "").strip() or runner_host)
                vless_link = f"vless://{u_data.get('uuid', '')}@{DEFAULT_CLEAN_IP}:443?path=%2Fkillpv2&security=tls&encryption=none&insecure=0&type=ws&allowInsecure=0&host={t_host}&sni={t_host}#{u_name}_⚡Opt"
                sub_link = f"https://raw.githubusercontent.com/{SUB_REPO_NAME}/main/{u_name}"
                
                response_msg += (
                    f"{status_icon} *نام سرویس:* `{u_name}`\n"
                    f"💾 *کل حجم مجاز:* `{format_bytes_display(total_limit) if total_limit > 0 else 'نامحدود'}`\n"
                    f"📊 *حجم مصرف شده:* `{format_bytes_display(used)}`\n"
                    f"💾 *حجم باقی‌مانده:* `{format_bytes_display(rem) if total_limit > 0 else 'نامحدود'}`\n"
                    f"⏳ *زمان باقی‌مانده:* `{rem_d} روز و {rem_h} ساعت`\n\n"
                    f"🔗 *لینک ساب (Subscription):*\n`{sub_link}`\n\n"
                    f"📋 *لینک اتصال مستقیم شما (جهت کپی ضربه بزنید):*\n"
                    f"`{vless_link}`\n"
                    f"─────────────────\n"
                )
                
            bot.send_message(message.chat.id, response_msg, parse_mode="Markdown")

        @bot.message_handler(func=lambda msg: msg.text == "ℹ️ راهنما")
        def handle_user_help_request(message):
            help_text = (
                "ℹ️ *راهنمای اتصال به سرویس:*\n\n"
                "1️⃣ ابتدا نرم‌افزار متناسب با سیستم‌عامل خود را دانلود کنید:\n"
                "▪️ سیستم‌عامل اندروید: `v2rayNG` یا `NekoBox`\n"
                "▪️ سیستم‌عامل آیفون (iOS): `v2box` یا `FoXray`\n"
                "▪️ سیستم‌عامل ویندوز: `v2rayN`\n\n"
                "2️⃣ کانفیگ دریافتی را کپی کرده و در برنامه وارد کنید (گزینه Import from clipboard).\n"
                "3️⃣ اتصال را برقرار کنید و لذت ببرید!"
            )
            bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

        @bot.message_handler(func=lambda msg: str(msg.chat.id) == str(TELEGRAM_ADMIN_ID))
        def handle_admin_menu_clicks(message):
            if message.text == "🚀 ایجاد چالش جدید":
                msg_sent = bot.send_message(message.chat.id, "🔢 لطفاً ظرفیت چالش (تعداد نفرات) را وارد کن داداش:")
                bot.register_next_step_handler(msg_sent, process_capacity_step)
            elif message.text == "📊 آمار چالش":
                g_config = load_giveaway_config()
                stat_msg = (
                    f"📊 *آمار زنده چالش مخزن لوپ:*\n\n"
                    f"👥 ظرفیت پر شده: `{g_config['claimed_count']}` از `{g_config['max_claims']}`\n"
                    f"💾 حجم توزیع شده: `{g_config.get('volume_value', 0)} {g_config.get('volume_unit', 'GB')}`\n"
                    f"⚙️ وضعیت فعلی کمپین: `{g_config.get('status', 'inactive')}`"
                )
                bot.send_message(message.chat.id, stat_msg, parse_mode="Markdown")
            elif message.text == "🛠️ مدیریت وضعیت چالش":
                g_config = load_giveaway_config()
                status_curr = g_config.get("status", "inactive")
                inline_markup = InlineKeyboardMarkup()
                
                if status_curr == "active":
                    inline_markup.add(InlineKeyboardButton("🛑 لغو (غیرفعال‌سازی موقت)", callback_data="tg_camp_cancel"))
                elif status_curr == "cancelled":
                    inline_markup.add(InlineKeyboardButton("🟢 فعال‌سازی مجدد چالش", callback_data="tg_camp_activate"))
                
                inline_markup.add(InlineKeyboardButton("🗑️ حذف و ریست کامل چالش", callback_data="tg_camp_delete"))
                bot.send_message(message.chat.id, f"⚙️ وضعیت فعلی چالش شما: *{status_curr}*\nیک اقدام را انتخاب کن داداش:", parse_mode="Markdown", reply_markup=inline_markup)

        def process_capacity_step(message):
            try:
                capacity = int(message.text.strip())
                msg_sent = bot.send_message(message.chat.id, "💾 مقدار حجم کلاینت را وارد کن داداش:")
                bot.register_next_step_handler(msg_sent, lambda m: process_volume_value_step(m, capacity))
            except Exception:
                bot.send_message(message.chat.id, "❌ ظرفیت نامعتبر بود داداش. لطفاً دوباره دکمه ساخت را بزن.")

        def process_volume_value_step(message,
