# 🤖 Jarvis – Telegram Remote System Assistant

![This is Jarvis!]((https://github.com/Artin-khodayari/Jarvis-bot/blob/main/assets/Jarvis.jpg))

Your **private remote-control bot** for Windows & Linux, powered by Telegram.  
Jarvis listens only to you, and turns chat commands into **system actions, UI automation, and desktop notifications**.  

---

## ✨ What Jarvis Can Do

### 🔒 Security
- Only your configured `chat_id` can use Jarvis.  
- Strangers get a polite **Access Denied**.

### 🖼️ System & Info
- `/screenshot [x y w h]` -> Capture full or cropped screenshots.  
- `/programs` -> List visible open apps (Windows only).  
- `/chrometabs` -> Show active Chrome tab titles.  

### ⚙️ Control
- `/shutdown <time>` -> Schedule shutdown (`5m`, `1h`, `3600`).  
- `/cancelshutdown` -> Cancel pending shutdown.  
- `/lock` -> Lock Windows session.  
- `/wake` -> Press Enter to wake display.  
- `/move <x> <y>` -> Move mouse cursor.  
- `/click <type>` -> Click (`left`, `right`, `double`).  

### 🔔 Notifications
- Send any text -> Jarvis pops up a **desktop notification** with your message.  

---

## 🛠️ Setup

1. Clone the repo:

```bash
git clone https://github.com/Artin-khodayari/jarvis-bot.git
cd jarvis-bot
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Edit `config.json`:

```json
{
  "chat_id": "YOUR_TELEGRAM_CHAT_ID",
  "api_key": "YOUR_BOT_TOKEN"
}
```

4. (Optional) Enable proxy:

```bash
export USE_PROXY=True
```

5. Run:

```bash
python main.py
```

Jarvis will greet you with:

```
🔔 Jarvis is online.
```

---

## 🧩 Command Cheat Sheet

| Command             | Action                   | OS                       |
|--------------------|-------------------------|
| /screenshot         | Capture screen |
| /programs           | List open apps |
| /chrometabs         | List Chrome tabs |
| /shutdown           | Schedule shutdown |
| /cancelshutdown     | Cancel shutdown |
| /lock               | Lock session |
| /wake               | Wake display|
| /move <x> <y>           | Move cursor |
| /click <type>         | Mouse click |
| Types of /click > left - right - double|

---

## ⚠️ Notes
- It only works on windows.

---

## 📜 License
MIT License – free to use, hack, and share.

