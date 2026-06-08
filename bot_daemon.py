import os
import time
import threading
import requests
import torch
import gc
import subprocess
import re
from transformers import AutoModelForCausalLM, AutoTokenizer

# --- تنظیمات: توکن را از متغیر محیطی بخوان (امن‌تر) ---
MODEL_NAME = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "TOKEN_خودت_را_اینجا_یا_در_ENV_بگذار")
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# اگر روی CPU خیلی کند بود، این را True کن تا اجرای کد تولیدی غیرفعال شود (امن‌تر)
DISABLE_CODE_EXECUTION = False

print("⏳ در حال بارگذاری مدل 1.5B...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16 if DEVICE == "cuda" else torch.float32,
    device_map=DEVICE,
    low_cpu_mem_usage=True,
)
print(f"✅ مدل روی {DEVICE} بارگذاری شد.")

# قفل برای جلوگیری از اجرای همزمان مدل (مدل thread-safe نیست)
model_lock = threading.Lock()


# ---------------------------------------------------------
# ابزارهای کمکی تلگرام (ارسال امن)
# ---------------------------------------------------------
def escape_markdown_v2(text: str) -> str:
    """escape کاراکترهای خاص MarkdownV2."""
    specials = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(specials)}])", r"\\\1", text)


def tg_request(method: str, payload: dict, timeout: int = 20):
    """درخواست به API تلگرام با بررسی خطا."""
    try:
        r = requests.post(f"{API_URL}/{method}", json=payload, timeout=timeout)
        data = r.json()
        if not data.get("ok"):
            print(f"⚠️ تلگرام خطا داد در {method}: {data.get('description')}")
        return data
    except Exception as e:
        print(f"⚠️ خطا در ارتباط با تلگرام ({method}): {e}")
        return None


def send_message(chat_id, text, reply_to=None, code_block=False):
    """
    ارسال پیام با تقسیم خودکار اگر طولانی بود.
    code_block=True یعنی متن را داخل بلاک کد بفرست.
    """
    MAX = 3900  # کمی کمتر از 4096 برای جا دادن نشانه‌های بلاک کد
    chunks = [text[i:i + MAX] for i in range(0, len(text), MAX)] or [""]
    for idx, chunk in enumerate(chunks):
        if code_block:
            body = escape_markdown_v2(chunk)
            payload = {
                "chat_id": chat_id,
                "text": f"```\n{body}\n```",
                "parse_mode": "MarkdownV2",
            }
        else:
            # برای متن عادی از parse_mode استفاده نمی‌کنیم تا خطای Markdown نگیریم
            payload = {"chat_id": chat_id, "text": chunk}
        if reply_to and idx == 0:
            payload["reply_to_message_id"] = reply_to
        tg_request("sendMessage", payload)


# ---------------------------------------------------------
# ابزارهای سیستم
# ---------------------------------------------------------
def web_search(query):
    try:
        print(f"🔍 جستجوی وب: {query}")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        url = "https://html.duckduckgo.com/html/"
        response = requests.get(url, headers=headers, params={"q": query}, timeout=10)
        snippets = re.findall(
            r'<a class="result__snippet".*?>(.*?)</a>', response.text, re.DOTALL
        )
        clean = [re.sub(r"<[^>]+>", "", s).strip() for s in snippets[:3]]
        return "\n".join(clean) if clean else "نتیجه مستقیمی پیدا نشد."
    except Exception as e:
        return f"خطا در سرچ وب: {str(e)}"


def execute_in_terminal(code_string):
    if DISABLE_CODE_EXECUTION:
        return None, "اجرای کد غیرفعال است."
    file_name = "sandbox_test.py"
    clean_code = re.sub(r"```python|```", "", code_string).strip()
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(clean_code)
    try:
        result = subprocess.run(
            ["python3", file_name], capture_output=True, text=True, timeout=12
        )
        ok = result.returncode == 0
        return ok, (result.stdout if ok else result.stderr)
    except subprocess.TimeoutExpired:
        return False, "خطا: زمان اجرای کد تمام شد."
    except Exception as e:
        return False, f"خطای ترمینال: {str(e)}"
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)


def ask_coder_llm(system_prompt, user_input, max_new_tokens=1024):
    with model_lock:  # جلوگیری از اجرای همزمان
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        model_inputs = tokenizer([text], return_tensors="pt").to(DEVICE)
        with torch.no_grad():
            generated_ids = model.generate(
                **model_inputs, max_new_tokens=max_new_tokens, do_sample=False
            )
        generated_ids = [
            out[len(inp):] for inp, out in zip(model_inputs.input_ids, generated_ids)
        ]
        result = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    gc.collect()
    return result


# ---------------------------------------------------------
# موتور پردازش (ساده‌تر و سریع‌تر)
# ---------------------------------------------------------
def process_autonomous_code(user_prompt, chat_id, message_id):
    try:
        tg_request("sendChatAction", {"chat_id": chat_id, "action": "typing"})
        print(f"📥 درخواست جدید: {user_prompt}")

        # یک‌بار صدا زدن مدل برای تولید کد (سریع‌تر روی CPU)
        dev_prompt = (
            "تو یک برنامه‌نویس ارشد پایتون هستی. کد پایتون تمیز و کامل بنویس. "
            "ابتدا یک توضیح کوتاه فارسی بده، سپس کد را داخل بلاک ```python بگذار."
        )
        full_answer = ask_coder_llm(dev_prompt, user_prompt, max_new_tokens=1024)

        # جدا کردن کد از توضیح
        code_match = re.search(r"```python(.*?)```", full_answer, re.DOTALL)
        if code_match:
            generated_code = code_match.group(1).strip()
            explanation = re.sub(r"```python.*?```", "", full_answer, flags=re.DOTALL).strip()
        else:
            generated_code = ""
            explanation = full_answer.strip()

        # تست و دیباگ (در صورت فعال بودن و وجود کد)
        is_success = None
        if generated_code and not DISABLE_CODE_EXECUTION:
            max_retries = 2
            for attempt in range(1, max_retries + 1):
                is_success, terminal_output = execute_in_terminal(generated_code)
                if is_success:
                    break
                debug_prompt = (
                    "تو یک دیباگر ارشد پایتون هستی. کد زیر خطا داده. "
                    "اصلاحش کن و فقط کد خالص داخل بلاک ```python برگردان."
                )
                fixed = ask_coder_llm(
                    debug_prompt,
                    f"کد معیوب:\n{generated_code}\n\nخطا:\n{terminal_output}",
                    max_new_tokens=1024,
                )
                m = re.search(r"```python(.*?)```", fixed, re.DOTALL)
                generated_code = m.group(1).strip() if m else fixed.strip()

        # ارسال نتیجه
        if is_success is True:
            status = "🟢 تست موفق"
        elif is_success is False:
            status = "🔴 تست ناموفق (کد ممکن است نیاز به بازبینی داشته باشد)"
        else:
            status = "⚪ بدون تست"

        send_message(
            chat_id,
            f"🛠 پروژه‌ات پردازش شد داداش!\n\n📊 وضعیت: {status}\n\n📝 توضیح:\n{explanation}",
            reply_to=message_id,
        )
        if generated_code:
            send_message(chat_id, generated_code, code_block=True)

    except Exception as e:
        print(f"⚠️ خطا در پردازش: {e}")
        send_message(chat_id, f"❌ متاسفانه خطایی رخ داد: {e}")
    finally:
        gc.collect()


# ---------------------------------------------------------
# حلقه شنود (بدون قفل شدن — پردازش در thread جدا)
# ---------------------------------------------------------
def start_polling():
    print("🧹 پاکسازی وب‌هوک قدیمی...")
    try:
        requests.get(f"{API_URL}/deleteWebhook", params={"drop_pending_updates": True}, timeout=10)
    except Exception:
        pass

    offset = 0
    print("✅ بات بیدار شد و آماده است...")

    while True:
        try:
            response = requests.get(
                f"{API_URL}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=40,
            )
            if response.status_code != 200:
                print(f"⚠️ خطای سرور تلگرام ({response.status_code}). ۵ ثانیه صبر...")
                time.sleep(5)
                continue

            updates = response.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message", {})
                text = message.get("text", "")
                chat_id = message.get("chat", {}).get("id")
                message_id = message.get("message_id")

                if text and chat_id:
                    # پردازش در thread جدا تا حلقه قفل نشود
                    threading.Thread(
                        target=process_autonomous_code,
                        args=(text, chat_id, message_id),
                        daemon=True,
                    ).start()
        except Exception as e:
            print(f"⚠️ خطای ناگهانی در حلقه اصلی: {e}. تلاش مجدد...")
            time.sleep(5)


if __name__ == "__main__":
    start_polling()
