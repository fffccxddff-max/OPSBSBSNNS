import telebot
import time
import os
import subprocess

def generate_qr_url(data_link):
    """تولید سریع و بدون نقص لینک مستقیم عکس QR دیتای کانفیگ بدون اشغال رم رانر"""
    import urllib.parse
    encoded_data = urllib.parse.quote(data_link)
    return f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&margin=10&data={encoded_data}"

def run_telegram_bot(bot_token, panel_db, host_domain):
    """مدیریت تحویل هوشمند کانفیگ همراه با ساب لینک و QR کد سفارشی"""
    if not bot_token or "YOUR_BOT" in bot_token:
        return
        
    bot = telebot.TeleBot(bot_token)
    
    @bot.message_handler(commands=['start', 'get_config'])
    def send_user_config(message):
        u_name = message.from_user.username or f"user_{message.from_user.id}"
        
        if u_name in panel_db:
            user_data = panel_db[u_name]
            uuid_val = user_data.get("uuid")
            # لینک ساب مستقیم بر اساس ساختار هسته
            sub_link = f"vless://{uuid_val}@{host_domain}:443?path=%2Fkillpv2&security=tls&encryption=none&type=ws#killpv2_{u_name}"
            qr_photo = generate_qr_url(sub_link)
            
            caption = (
                f"🎯 **کانفیگ اختصاصی شما آماده شد داداش!**\n\n"
                f"👤 نام کاربری: `{u_name}`\n"
                f"🔗 لینک ساب مستقیم:\n`{sub_link}`\n\n"
                f"📱 برای اتصال راحت، کد QR بالا را داخل برنامه اسکن کن."
            )
            try:
                bot.send_photo(message.chat.id, qr_photo, caption=caption, parse_mode="Markdown")
            except Exception:
                bot.reply_to(message, caption, parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ داداش اسمت هنوز توی دیتابیس ثبت نشده، ابتدا از طریق پنل کاربری برات اکانت بساز.")

    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=10)
    except Exception:
        pass

def start_live_rtmp_stream(channel_id):
    """
    استریم لایو و هوشمند فید لاگ‌های مدیریتی به صورت شیر اسکرین روی لایو چنل تلگرام
    از ابزار بومی ffmpeg برای تبدیل دیتای متنی به فریم‌های ویدیویی فوق العاده سبک استفاده می‌کند.
    """
    # در صورتی که کلید استریم تلگرام در چنل ست شده باشد، کدهای زیر فید را به صورت ویدیو رندر می‌کنند
    stream_key = os.environ.get("TELEGRAM_STREAM_KEY", "")
    if not stream_key or not channel_id:
        return

    rtmp_url = f"rtmp://127.0.0.1/live/{stream_key}" # آدرس گیت استریم تلگرام شما
    
    # دستور ساخت یک ویدیو زنده ترمینالی از لاگ‌های سیستم و ارسال آن به چنل تلگرام به صورت لایو کامپایلر
    ffmpeg_cmd = (
        f"ffmpeg -f lavfi -i color=c=black:s=1280x720:r=10 -f lmlm -re -i /usr/local/etc/xray/xray_runtime.log "
        f"-c:v libx264 -pix_fmt yuv420p -preset ultrafast -f flv {rtmp_url}"
    )
    
    while True:
        try:
            if os.path.exists("/usr/local/etc/xray/xray_runtime.log"):
                subprocess.run(ffmpeg_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        time.sleep(5) # قابلیت اتصال مجدد خودکار در صورت نوسان شبکه رانر
