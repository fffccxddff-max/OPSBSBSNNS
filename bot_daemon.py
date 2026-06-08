import os
import sys
import time
import requests
import torch
import gc
import subprocess
import re
from transformers import AutoModelForCausalLM, AutoTokenizer

# --- تنظیمات توکن و مدل 1.5B ---
MODEL_NAME = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
TELEGRAM_TOKEN = "8940324884:AAEZPFjiZlUKd1iuNT4QPBZ6vr0f2ee593c"
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

print("⏳ در حال بارگذاری مدل قدرتمند 1.5B به صورت محلی روی سرور گیت‌هاب...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME, 
    torch_dtype=torch.bfloat16, 
    device_map="cpu",
    low_cpu_mem_usage=True
)

# ---------------------------------------------------------
# 🛠 ابزارهای سیستم (ترمینال + سرچ وب)
# ---------------------------------------------------------

def web_search(query):
    try:
        print(f"🔍 در حال جستجوی وب برای: {query}")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        url = f"https://html.duckduckgo.com/html/?q={query}"
        response = requests.get(url, headers=headers, timeout=10)
        snippets = re.findall(r'<a class="result__snippet".*?>(.*?)</a>', response.text, re.DOTALL)
        clean_snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:3]]
        return "\n".join(clean_snippets) if clean_snippets else "نتیجه مستقیمی پیدا نشد."
    except Exception as e:
        return f"خطا در سرچ وب: {str(e)}"

def execute_in_terminal(code_string):
    file_name = "sandbox_test.py"
    clean_code = re.sub(r'```python|```', '', code_string).strip()
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(clean_code)
    try:
        result = subprocess.run(["python3", file_name], capture_output=True, text=True, timeout=12)
        return (True, result.stdout) if result.returncode == 0 else (False, result.stderr)
    except subprocess.TimeoutExpired:
        return False, "خطا: زمان اجرای کد اکسپایر شد."
    except Exception as e:
        return False, f"خطای ترمینال: {str(e)}"

def ask_coder_llm(system_prompt, user_input):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([text], return_tensors="pt")
    generated_ids = model.generate(**model_inputs, max_new_tokens=1200, do_sample=False)
    generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)]
    return tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

# ---------------------------------------------------------
# 🚀 موتور پردازش ۵ شارده
# ---------------------------------------------------------
def process_autonomous_code(user_prompt, chat_id, message_id):
    requests.post(f"{API_URL}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
    print(f"📥 دریافت درخواست جدید: {user_prompt}")
    
    search_context = web_search(user_prompt)
    
    think_prompt = "تو یک مهندس معمار الگوریتم هستی. ساختار و الزامات دقیق مورد نیاز کد را گام به گام بدون نوشتن خود کد بنویس."
    logic_plan = ask_coder_llm(think_prompt, f"درخواست: {user_prompt}\nداده وب:\n{search_context}")
    
    dev_prompt = "تو یک برنامه نویس ارشد پایتون هستی. فقط و فقط کد خالص پایتون بنویس. هیچ کلمه اضافه‌ای بیرون از بلاک کد ننویس."
    generated_code = ask_coder_llm(dev_prompt, logic_plan)
    
    max_retries, attempt, is_success, terminal_output = 3, 0, False, ""
    while attempt < max_retries:
        attempt += 1
        is_success, terminal_output = execute_in_terminal(generated_code)
        if is_success: break
        
        debug_prompt = "تو یک دیباگر ارشد هستی. کد زیر خطا داده، اصلاحش کن و فقط کد خالص بدون توضیح برگردان."
        generated_code = ask_coder_llm(debug_prompt, f"کد معیوب:\n{generated_code}\n\nخطا:\n{terminal_output}")
            
    delivery_prompt = "تو مدیر دلیوری پروژه هستی. یک راهنمای فارسی بسیار کوتاه برای اجرای این کد بنویس. خود کد را در متن نگذار."
    explanations = ask_coder_llm(delivery_prompt, f"درخواست: {user_prompt}\nموفقیت: {is_success}")
    
    final_clean_code = re.sub(r'```python|```', '', generated_code).strip()
    status_icon = "🟢" if is_success else "🔴"
    
    report_message = f"🛠 **پروژه شما پردازش شد داداش!**\n\n📊 **تست ترمینال:** {status_icon}\n\n📝 **راهنما:**\n{explanations}"
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": report_message, "parse_mode": "Markdown", "reply_to_message_id": message_id})
    
    code_message = f"💻 **کد اصلی و نهایی (بی خطا):**\n```python\n{final_clean_code}\n```"
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": code_message, "parse_mode": "Markdown"})
    
    if os.path.exists("sandbox_test.py"): os.remove("sandbox_test.py")
    gc.collect()

# ---------------------------------------------------------
# چرخه هوشمند و جان‌سخت شنود
# ---------------------------------------------------------
def start_polling():
    # گام طلایی: حذف هرگونه وب‌هوک یا اتصال مرده قدیمی برای جلوگیری از خطای ۴۰۹
    print("🧹 در حال پاکسازی اتصالات و وب‌هوک‌های قدیمی تلگرام...")
    try:
        requests.get(f"{API_URL}/deleteWebhook")
    except Exception:
        pass

    offset = 0
    try:
        init_resp = requests.get(f"{API_URL}/getUpdates", params={"offset": -1, "timeout": 1}, timeout=5)
        if init_resp.status_code == 200 and init_resp.json().get("result"):
            offset = init_resp.json()["result"][0]["update_id"] + 1
            print("✅ صف پیام‌های قدیمی با موفقیت تخلیه شد.")
    except Exception:
        pass

    print("✅ غول محلی 1.5B بیدار شد داداش! سیستم آماده و گوش‌به‌زنگ است...")
    
    while True:
        try:
            response = requests.get(f"{API_URL}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            
            # رفع باگ بزرگ: اگر خطای تداخل داد، دیگر اسکریپت را نمی‌بندیم!
            if response.status_code == 409 or response.status_code != 200:
                print(f"⚠️ تداخل یا خطای سرور تلگرام ({response.status_code}). ۵ ثانیه صبر...")
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
                    process_autonomous_code(text, chat_id, message_id)
        except Exception as e:
            print(f"⚠️ خطای ناگهانی در چرخه اصلی: {e}. تلاش مجدد...")
            time.sleep(5)

if __name__ == "__main__":
    start_polling()
