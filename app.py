import os
import json
from datetime import datetime, timedelta
import pytz
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# 設定
DATA_FILE = 'data.json'
JST = pytz.timezone('Asia/Tokyo')
MAX_SECONDS = 3 * 60 * 60  # 3時間

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"records": {}, "active_session": None}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_now_jst():
    return datetime.now(JST)

def process_session_end(data):
    """セッションを終了し、時間を記録する（3時間制限と日付またぎ対応）"""
    session = data["active_session"]
    if not session:
        return

    start_time = datetime.fromisoformat(session["start_time"])
    now = get_now_jst()
    
    # 最大3時間までの制限
    end_time = min(now, start_time + timedelta(seconds=MAX_SECONDS))
    
    duration = (end_time - start_time).total_seconds()
    
    # 日付をまたぐ場合の計算
    current_dt = start_time
    while current_dt.date() <= end_time.date():
        # その日の終わり（23:59:59）か、終了時刻の早い方
        day_end = datetime.combine(current_dt.date(), datetime.max.time()).replace(tzinfo=JST)
        actual_end = min(end_time, day_end)
        
        day_sec = (actual_end - current_dt).total_seconds()
        date_str = current_dt.strftime('%Y-%m-%d')
        
        if date_str not in data["records"]:
            data["records"][date_str] = {"english": 0, "piano": 0}
        
        data["records"][date_str][session["type"]] += round(day_sec / 60) # 分単位で保存
        
        if actual_end == end_time:
            break
        current_dt = datetime.combine(current_dt.date() + timedelta(days=1), datetime.min.time()).replace(tzinfo=JST)

    data["active_session"] = None
    save_data(data)

@app.route('/')
def index():
    data = load_data()
    now = get_now_jst()
    
    # 自動終了チェック (ページ読み込み時に3時間を超えていたら終了させる)
    if data["active_session"]:
        start_time = datetime.fromisoformat(data["active_session"]["start_time"])
        if (now - start_time).total_seconds() >= MAX_SECONDS:
            process_session_end(data)
            data = load_data()

    selected_date = request.args.get('date', now.strftime('%Y-%m-%d'))
    
    # 表示用データ
    day_record = data["records"].get(selected_date, {"english": 0, "piano": 0})
    
    # 日付選択肢（今日から過去30日分）
    date_options = [(now - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
    
    return render_template('index.html', 
                           record=day_record, 
                           active_session=data["active_session"],
                           selected_date=selected_date,
                           date_options=date_options)

@app.route('/start', methods=['POST'])
def start():
    data = load_data()
    if not data["active_session"]:
        data["active_session"] = {
            "type": request.form.get('type'),
            "start_time": get_now_jst().isoformat()
        }
        save_data(data)
    return redirect(url_for('index'))

@app.route('/stop', methods=['POST'])
def stop():
    data = load_data()
    process_session_end(data)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)