import os
import json
from datetime import datetime, timedelta
import pytz
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

DEFAULT_DATA_FILE = 'data.json'
JST = pytz.timezone('Asia/Tokyo')
MAX_SECONDS = 3 * 60 * 60


def get_data_file_path():
    env_path = os.getenv('LEARNING_RECORD_DATA_FILE')
    if env_path:
        return env_path

    home_dir = os.path.expanduser('~')
    if home_dir:
        candidate = os.path.join(home_dir, 'learningrecord', 'data.json')
        return candidate

    return DEFAULT_DATA_FILE


DATA_FILE = get_data_file_path()


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"records": {}, "active_session": None}

def save_data(data):
    directory = os.path.dirname(DATA_FILE)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_now_jst():
    return datetime.now(JST)

def format_minutes(total_minutes):
    total_minutes = int(total_minutes)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}時間{minutes}分"

def calculate_and_add(data, session_type, start_dt, end_dt):
    """時間を計算して日付ごとに配分する共通ロジック"""
    current_dt = start_dt
    while current_dt < end_dt:
        day_end = datetime.combine(current_dt.date(), datetime.max.time()).replace(tzinfo=JST)
        actual_end = min(end_dt, day_end)
        
        duration_sec = (actual_end - current_dt).total_seconds()
        date_str = current_dt.strftime('%Y-%m-%d')
        
        if date_str not in data["records"]:
            data["records"][date_str] = {"english": 0, "piano": 0}
        
        # 秒単位の蓄積を許容し、表示時に分にする（精度向上のため）
        data["records"][date_str][session_type] += duration_sec
        
        current_dt = datetime.combine(current_dt.date() + timedelta(days=1), datetime.min.time()).replace(tzinfo=JST)

@app.route('/')
def index():
    data = load_data()
    now = get_now_jst()
    
    # 3時間制限の自動終了チェック
    if data["active_session"]:
        start_time = datetime.fromisoformat(data["active_session"]["start_time"])
        if (now - start_time).total_seconds() >= MAX_SECONDS:
            stop() # 自動終了
            data = load_data()

    selected_date = request.args.get('date', now.strftime('%Y-%m-%d'))
    day_record = data["records"].get(selected_date, {"english": 0, "piano": 0})
    
    # 秒を分に変換して表示（小数点切り捨て）
    display_record = {
        "english": int(day_record["english"] // 60),
        "piano": int(day_record["piano"] // 60),
        "english_text": format_minutes(int(day_record["english"] // 60)),
        "piano_text": format_minutes(int(day_record["piano"] // 60))
    }

    date_options = [(now - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
    
    return render_template('index.html', 
                           record=display_record, 
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
    if data["active_session"]:
        start_time = datetime.fromisoformat(data["active_session"]["start_time"])
        now = get_now_jst()
        end_time = min(now, start_time + timedelta(seconds=MAX_SECONDS))
        
        calculate_and_add(data, data["active_session"]["type"], start_time, end_time)
        data["active_session"] = None
        save_data(data)
    return redirect(url_for('index'))

@app.route('/update_midway', methods=['POST'])
def update_midway():
    """バックグラウンドで途中経過を保存するAPI"""
    data = load_data()
    if data["active_session"]:
        start_time = datetime.fromisoformat(data["active_session"]["start_time"])
        now = get_now_jst()
        
        # 3時間を超えていないかチェック
        if (now - start_time).total_seconds() <= MAX_SECONDS:
            # 今回の増分を計算して保存し、開始時刻を「今」に更新する
            calculate_and_add(data, data["active_session"]["type"], start_time, now)
            data["active_session"]["start_time"] = now.isoformat()
            save_data(data)
            return jsonify({"status": "success"})
    return jsonify({"status": "no_active_session"})

if __name__ == '__main__':
    app.run(debug=False)