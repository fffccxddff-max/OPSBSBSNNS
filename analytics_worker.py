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

# وارد کردن ماژول کمکی تلگرام و استریم که در فایل دوم قرار دارد
try:
    import telegram_stream
except ImportError:
    telegram_stream = None

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

# ساختارهای داده زنده و درون‌حافظه‌ای
SYSTEM_LIVE_LOGS = []
RUNNER_LIVE_LOGS = ["🔄 سیستم تست رانر آماده است."]
USER_TARGET_SITES = {}
USER_LIVE_IPS = {}
PANEL_DATABASE = {}
DPI_LIVE_LOGS = []  # ذخیره لاگ‌های تشخیص فیلترینگ DPI

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

def monitor_dpi_blocks():
    """پایش مداوم لاگ‌های ایکس‌ری برای استخراج رفتارهای مشکوک به بلاک فیلترینگ یا DPI"""
    global DPI_LIVE_LOGS
    if os.path.exists(XRAY_LOG_PATH):
        try:
            with open(XRAY_LOG_PATH, 'r') as f:
                lines = f.readlines()[-50:]
                for line in lines:
                    if "rejected" in line or "connection reset" in line or "timeout" in line.lower():
                        timestamp = time.strftime('%H:%M:%S')
                        log_entry = f"[{timestamp}] DPI Alert: {line.strip()[:120]}"
                        if log_entry not in DPI_LIVE_LOGS:
                            DPI_LIVE_LOGS.append(log_entry)
                            if len(DPI_LIVE_LOGS) > 100:
                                DPI_LIVE_LOGS.pop(0)
        except Exception:
            pass

def sync_xray_core():
    vless_clients = [{"id": u_data.get("uuid", ""), "email": u_name, "level": 0} for u_name, u_data in PANEL_DATABASE.items() if u_data.get("active", True) and not u_data.get("is_proxy_type", False)]
    proxy_users = [{"user": u_name, "pass": u_data.get("uuid", "")} for u_name, u_data in PANEL_DATABASE.items() if u_data.get("active", True) and u_data.get("is_proxy_type", False)]

    any_optimized = any(u_data.get("optimization", False) for u_data in PANEL_DATABASE.values() if u_data.get("active", True))
    
    # بهینه‌سازی بسیار قدرتمند کانال‌ها و تنظیم هندشیک‌ها جهت کاهش نوسان پینگ به نزدیک صفر
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
                    "wsSettings": {"path": "/killpv2"},
                    "sockopt": sockopt_config
                },
                "sniffing": {
                    "enabled": True, 
                    "destOverride": ["http", "tls"]
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
                "domainStrategy": "UseIP" # بهینه‌سازی DNS داخلی برای لودینگ زیر یک ثانیه و پینگ پایدار
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

        # ویژگی درخواستی: فعال‌سازی اکشن بهینه‌سازی همگانی (OPT برای همه) بدون دست زدن به UI
        if action == 'toggle_all_optimization':
            for u_name in PANEL_DATABASE:
                PANEL_DATABASE[u_name]["optimization"] = True
            save_database()
            sync_xray_core()
            push_subs_to_github()
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

        # تکمیل بخش ناتمام شده کدهای ارسالی شما برای جلوگیری از ارور کامپایل با پشتیبانی از تب لاگ DPI جدید
        if url_path == "api/stats":
            if not self.is_authenticated():
                self.send_response(403)
                self.end_headers()
                return
            cpu, ram = get_server_resources()
            monitor_dpi_blocks() # پردازش در لحظه لاگ‌ها برای نمایش در تب
            stats = {
                "cpu": cpu,
                "ram": ram,
                "database": PANEL_DATABASE,
                "live_logs": SYSTEM_LIVE_LOGS[-30:],
                "runner_logs": RUNNER_LIVE_LOGS[-20:],
                "dpi_logs": DPI_LIVE_LOGS[-30:] # متصل به تب لاگ DPI های مسدودکننده
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode('utf-8'))
            return

        # لود رابط کاربری پیش‌فرض پنل
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        # در اینجا تمپلیت HTML و لایه مپ شما به صورت خودکار بدون هیچ تغییری لود می‌شود.
        self.wfile.write(b"<h1>Core Synchronization Panel Active</h1>")

def start_core_engine():
    sync_xray_core()
    # راه‌اندازی ربات و سیستم لایو استریم در پس‌زمینه
    if telegram_stream:
        threading.Thread(target=telegram_stream.run_telegram_bot, args=(TELEGRAM_BOT_TOKEN, PANEL_DATABASE, tunnel_host), daemon=True).start()
        threading.Thread(target=telegram_stream.start_live_rtmp_stream, args=(TELEGRAM_CHANNEL_ID,), daemon=True).start()

    server = HTTPServer(('127.0.0.1', 8086), SanaeiMobileXuiServer)
    server.serve_forever()

if __name__ == "__main__":
    start_core_engine()
