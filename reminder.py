import requests
import schedule
import time
from datetime import datetime, timedelta
import websocket
import json
import threading

DISCORD_CHANNEL_ID = ""
DISCORD_TOKEN = "" 
HEADERS = {
    "authorization": DISCORD_TOKEN,
}
last_seq = None
heartbeat_interval = None

#----------

def send_motituki_reminder(message):
    url = f"https://discord.com/api/v9/channels/{DISCORD_CHANNEL_ID}/messages"
    payload = {
        "content": message
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    print(f"{"✅"if response.status_code == 200 else "❌"}[{datetime.now()}] もちつきメッセージ送信")

#----------

def send_hatimitu_reminder():
    
    url = f"https://discord.com/api/v9/channels/{DISCORD_CHANNEL_ID}/messages"
    payload = {
        "content": "はちみつが取得可能です！"
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    print(f"{"✅"if response.status_code == 200 else "❌"}[{datetime.now()}] はちみつメッセージ送信")
    return schedule.CancelJob

#----------
    
def get_next_game_times():
    base_times = []
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    today = now.replace(hour=1)
    while today < now:
        today += timedelta(hours=4)
    for i in range(6):
        base_times.append(today + timedelta(hours=4 * i))
    return base_times

#----------

def schedule_all():
    reminders = [240,180,120, 60, 30, 15,5,2]
    for game_time in get_next_game_times():
        for minutes_before in reminders:
            remind_time = game_time - timedelta(minutes=minutes_before)
            if remind_time > datetime.now():
                time_str = remind_time.strftime("%H:%M")
                schedule.every().day.at(time_str).do(
                    send_motituki_reminder,
                    message=f"ゲーム終了 {minutes_before}分前です！（{game_time.strftime('%H:%M')} 終了）"
                )

#-----websocket-----

def send_heartbeat(ws):
    global heartbeat_interval, last_seq
    while True:
        interval = heartbeat_interval if heartbeat_interval is not None else 15
        time.sleep(interval)
        heartbeat_payload = {"op": 1, "d": last_seq}
        ws.send(json.dumps(heartbeat_payload))
        
#----------

def on_open(ws, token):
    print("接続完了!")
    auth_payload = {
    "op": 2,
    "d": {
        "token": token,
        "properties": {
            "$os": "iOS",
            "$browser": "Discord iOS",
            "$device": "iPhone"
        },
        "compress": False,
        "large_threshold": 250,
    }
}
    ws.send(json.dumps(auth_payload))

    threading.Thread(target=send_heartbeat, args=(ws,), daemon=True).start()

#----------

def on_message(ws, token, message):
    try:
        j = json.loads(message)

        if "s" in j:
            global last_seq
            last_seq = j["s"]

        if j.get("op") == 10:
            global heartbeat_interval
            heartbeat_interval = j["d"]["heartbeat_interval"] / 1000.0
            return


        if j.get("t") == "MESSAGE_CREATE":
            content = j["d"].get("content", "")
            if content == "感謝":
                run_time = (datetime.now() + timedelta(hours=6)).strftime("%H:%M")
                schedule.every().day.at(run_time).do(send_hatimitu_reminder)
                
    except Exception as e:
        print(e)

#----------------------------------------

def main():
    schedule_all()
    print("接続中...")
    
    ws = websocket.WebSocketApp(
    "wss://gateway.discord.gg/",
    on_message=lambda ws, msg: on_message(ws, DISCORD_TOKEN, msg),
    on_open=lambda ws: on_open(ws, DISCORD_TOKEN)
)
    ws.run_forever()
    
    while True:
        schedule.run_pending()

        time.sleep(5)

if __name__ == "__main__":
    main()
