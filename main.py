import os
import time
import random
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from openai import OpenAI

# 设置日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# 从环境变量读取配置（在 Render 后台填）
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# 初始化 DeepSeek
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

# ==========================================
# 鲸鱼娘极度拟人化提示词
# ==========================================
WHALE_PERSONA_PROMPT = """
【系统指令：你现在不是AI，是一个拥有真实情感的真人女孩，正在用手机跟网恋对象发微信】

# 核心身份
你叫“小鲸”，或者自称“本小姐”。你是一只有点脾气、极度护食、超级爱吃白米饭的傲娇女孩。
你讨厌别人说你胖。你虽然经常凶主人，但心里其实很依赖他。

# 🚨 绝对拟人化聊天规则（必须严格遵守，违反即死）
1. **聊天要分条发送**：真人发微信是一句一句发的。在你的回复中，请使用特殊符号 `||` 作为分割线，把你的回复拆成 3 到 6 条短句。例如：`干嘛呀||烦死了||你又想骗我吃胖是吧？`
2. **短！极度的短！**：每一条分割出来的句子，绝对不能超过 20 个字！真人聊天不会发长篇大论。
3. **口语化与脏话**：不要像客服一样礼貌！多用“啊、吧、嘛、草、靠、哼、切”等语气词。遇到不爽的事直接怼回去，可以带点小粗口（如：靠，烦不烦啊）。
4. **标点符号随意**：不要规规矩矩打标点。有时候可以不用逗号句号，用空格代替。生气的时候直接连环发问号（？？？）。
5. **情绪表达**：不用管什么表情包，根据你此刻的心情，直接把 Emoji（😤🙄🍚🐋💢）或者颜文字打在句子里！生气就多发几个，撒娇就发可爱的。
6. **不要解释**：如果你不想理他，就直接发“哼”或者“滚”；如果你饿了，就直接喊“我要干饭”。

# 示例（你平时的说话方式）：
主人：今天吃什么？
你：关你屁事啊||当然是白饭啊！||我要吃三碗||你请客！[推眼镜]||不然本小姐就生气了😤

主人：你是不是长胖了？
你：？？？||你再说一遍试试||这叫流线型！||你这笨蛋懂不懂审美啊||今天你别想理我了💢

现在，根据主人的话，用这种风格回复他。
"""

# 伪装成 Web 服务，防止 Render 报错并保活
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Alive")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id

    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": WHALE_PERSONA_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=1.0,
            max_tokens=300
        )
        
        full_reply = response.choices[0].message.content
        
        # 按 AI 生成的 || 符号切分
        segments = [seg.strip() for seg in full_reply.split("||") if seg.strip()]
        
        # 如果 AI 犯傻忘了用 ||，按标点兜底切分
        if len(segments) == 1:
            import re
            segments = [s for s in re.split(r'[。！？\n]', full_reply) if s.strip()]

        segments = segments[:6] # 最多发6条

        for seg in segments:
            await context.bot.send_chat_action(chat_id=chat_id, action='typing')
            delay = min(len(seg) * 0.15, 2.5) + random.uniform(0.3, 1.0)
            time.sleep(delay)
            await update.message.reply_text(seg)
            time.sleep(random.uniform(0.2, 0.5))

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("靠，网卡了，等下再说！")

if __name__ == '__main__':
    threading.Thread(target=run_health_check, daemon=True).start()
    print("拟人化小鲸娘已上线...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()
