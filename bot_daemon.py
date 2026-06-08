import os
import sys
import time
import requests
import torch
import gc
import subprocess
import re
from transformers import AutoModelForCausalLM, AutoTokenizer

# --- تنظیمات اولیه و بارگذاری مدل ۱ گیگابایتی کاملاً محلی ---
MODEL_NAME = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
TELEGRAM_TOKEN = "8940324884:AAGZLh7pJ1go9JmWdlMnaoD6j2wWRAnpADY"
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

print("⏳ در حال بارگذاری مدل هوش مصنوعی کاملاً محلی روی سرور گیت‌هاب...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# لود سبک و فوق‌سریع در رم گیت‌هاب بدون خطر کرش (OOM)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME, 
    torch_dtype=torch.bfloat16, 
    device_map="cpu",
    low_cpu_mem_usage=True
)
print("✅ غول محلی بیدار شد داداش! سیستم آماده است و شنود تلگرام شروع شد...")

# ---------------------------------------------------------
# 🛠 ابزارهای بومی ایجنت (ترمینال + سرچ وب)
# ---------------------------------------------------------

def web_search(query):
    """ابزار سرچ اختصاصی در وب"""
    try:
        print(f"🔍 در حال جستجوی وب برای: {query}")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        url = f"https://html.duckduckgo.com/html/?q={query}"
        response = requests.get(url, headers=headers, timeout=10)
        
        snippets = re.findall(r'<a class="result__snippet".*?>(.*?)</a>', response.text, re.DOTALL)
        clean_snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:3]]
        
        if clean_snippets:
            return "\n".join(clean_snippets)
        return "نتیجه مستقیمی در سرچ پیدا نشد."
    except Exception as e:
        return f"خطا در سرچ وب: {str(e)}"

def execute_in_terminal(code_string):
    """ابزار ترمینال: اجرای واقعی کد روی لینوکس اوبونتو"""
    file_name = "sandbox_test.py"
    clean_code = re.sub(r'```python|```', '', code_string).strip()
    
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(clean_code)
    
    try:
        result = subprocess.run(
            ["python3", file_name], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "خطا: زمان اجرای کد بیش از حد طولانی شد."
    except Exception as e:
        return False, f"خطای سیستمی ترمینال: {str(e)}"

def ask_coder_llm(system_prompt, user_input):
    """رابط گفتگو با مدل محلی"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([text], return_tensors="pt")
    
    generated_ids = model.generate(
        **model_inputs, 
        max_new_tokens=1000, 
        do_sample=False
    )
    generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)]
    return tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

# ---------------------------------------------------------
# 🚀 موتور پردازش ۶ عامله (با چرخه عیب‌یابی خودکار)
# ---------------------------------------------------------
def process_autonomous_code(user_prompt, chat_id, message_id):
    requests.post(f"{API_URL}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})
    print(f"📥 دریافت درخواست جدید از تلگرام: {user_prompt}")
    
    print("🤖 شارد ۱: تحقیق در وب...")
    search_context = web_search(user_prompt)
    
    print("🤖 شارد ۲: طراحی منطق برنامه...")
    think_prompt = "تو یک معمار نرم‌افزار هستی. منطق برنامه را گام به گام بنویس. کدی ننویس."
    logic_plan = ask_coder_llm(think_prompt, f"درخواست: {user_prompt}\nنتایج سرچ:\n{search_context}")
    
    print("🤖 شارد ۳: تولید کد اولیه پایتون...")
    dev_prompt = "تو برنامه‌نویس ارشد هستی. بر اساس منطق زیر، فقط کد خالص پایتون بنویس. هیچ توضیح اضافه‌ای نده."
    generated_code = ask_coder_llm(dev_prompt, logic_plan)
    
    print("🤖 شارد ۴ و ۵: تست ترمینال و دیباگ خودکار...")
    max_retries = 3
    attempt = 0
    is_success = False
    terminal_output = ""
    
    while attempt < max_retries:
        attempt += 1
        print(f"🧪 تست کد در ترمینال (تلاش {attempt} از {max_retries})...")
        is_success, terminal_output = execute_in_terminal(generated_code)
        
        if is_success:
            print("✅ کد بدون باگ تایید شد!")
            break
        else:
            print(f"❌ ترمینال خطا داد! ارجاع به شارد دیباگر...")
            debug_prompt = "تو یک دیباگر ارشد هستی. کد زیر را بر اساس خطای ترمینال کاملا اصلاح کن. فقط کد خالص بدون توضیح."
            generated_code = ask_coder_llm(debug_prompt, f"کد باگ‌دار:\n{generated_code}\n\nخطای ترمینال:\n{terminal_output}")
            
    print("🤖 شارد ۶: آماده‌سازی گزارش نهایی...")
    delivery_prompt = "تو مسئول تحویل پروژه هستی. یک راهنمای فارسی کوتاه برای این کد بنویس. خود کد را در متن نگذار."
    explanations = ask_coder_llm(delivery_prompt, f"درخواست: {user_prompt}\nوضعیت تست: {is_success}")
    
    # ارسال به تلگرام
    status_icon = "🟢" if is_success else "🔴"
    report_message = (
        f"🛠 **پروژه شما در سیستم محلی گیت‌هاب پردازش شد داداش!**\n\n"
        f"📊 **وضعیت تست ترمینال اوبونتو:** {status_icon} { 'بدون خطا' if is_success else 'دارای خطا' }\n\n"
        f"📝 **راهنما:**\n{explanations}"
    )
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": report_message, "parse_mode": "Markdown", "reply_to_message_id": message_id})
    
    code_message = f"💻 **کد نهایی:**\n```python\n{generated_code}\n```"
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": code_message, "parse_mode": "Markdown"})
    
    if not is_success:
        error_message = f"⚠️ **خطای رفع نشده:**\n```text\n{terminal_output}\n```"
        requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": error_message, "parse_mode": "Markdown"})
        
    if os.path.exists("sandbox_test.py"):
        os.remove("sandbox_test.py")
    gc.collect()

# ---------------------------------------------------------
# چرخه شنود تلگرام (Long Polling)
# ---------------------------------------------------------
def start_polling():
    offset = 0
    while True:
        try:
            response = requests.get(f"{API_URL}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            if response.status_code == 409:
                break
            if response.status_code != 200:
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
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    start_polling()
