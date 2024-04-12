from flask import Flask, request, jsonify, send_file, redirect
from models import Base, Timezone, BusinessHours, StoreActivity
from dbConnect import engine, session
from datetime import datetime, timedelta
import pytz
import pandas as pd
import uuid
from flask_caching import Cache
import os
import threading

app = Flask(__name__)

CACHE_CONFIG = {
    'CACHE_TYPE': 'simple',  
    'CACHE_DEFAULT_TIMEOUT': 3600
}

cache = Cache(config=CACHE_CONFIG)
cache.init_app(app)

Base.metadata.create_all(engine)

@app.route("/")
def index():
    return "Hello World"

@cache.cached(timeout=3600, key_prefix='timezone_data')
def get_timezone_data():
    return {tz.store_id: tz.timezone_str for tz in session.query(Timezone.store_id, Timezone.timezone_str)}

@cache.cached(timeout=3600, key_prefix='business_hours_data')
def get_business_hours_data():
    return {bh.store_id: (bh.start_time_local.strftime('%H:%M:%S'), bh.end_time_local.strftime('%H:%M:%S')) for bh in session.query(BusinessHours.store_id, BusinessHours.start_time_local, BusinessHours.end_time_local)}

@cache.cached(timeout=3600, key_prefix='store_activities')
def get_store_activities():
    return session.query(StoreActivity).all()

@cache.memoize(timeout=3600)
def generate_report_data(timezone_data, business_hours_data, store_activities):
    try:
        max_timestamp = max(activity.timestamp_utc for activity in store_activities)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

    def get_offset_hours(timezone_str):
        tz = pytz.timezone(timezone_str)
        return tz.utcoffset(max_timestamp).total_seconds() / 3600

    def is_active(activity_time, start_time, end_time):
        return start_time <= activity_time.strftime('%H:%M:%S') <= end_time

    store_activity_dict = {}
    for activity in store_activities:
        store_id = activity.store_id
        if store_id not in store_activity_dict:
            store_activity_dict[store_id] = []

        timezone_offset = get_offset_hours(timezone_data.get(store_id, 'America/Chicago'))
        timestamp_local = activity.timestamp_utc + timedelta(hours=timezone_offset)

        start_time, end_time = business_hours_data.get(store_id, ("00:00:00", "23:59:59"))
        if is_active(timestamp_local, start_time, end_time):
            status = 'active' if activity.status == 'active' else 'not active'
            store_activity_dict[store_id].append({'timestamp_utc': activity.timestamp_utc, 'status': status})

    final_report_data = []
    for store_id, activities in store_activity_dict.items():
        uptime_last_hour = sum(1 for activity in activities if activity['timestamp_utc'].hour == max_timestamp.hour and activity['status'] == 'active') * 15
        downtime_last_hour = sum(1 for activity in activities if activity['timestamp_utc'].hour == max_timestamp.hour and activity['status'] != 'active') * 15

        uptime_last_day = sum(1 for activity in activities if activity['timestamp_utc'].date() == max_timestamp.date() and is_active(activity['timestamp_utc'], *business_hours_data.get(store_id, ("00:00:00", "23:59:59"))) and activity['status'] == 'active')
        downtime_last_day = sum(1 for activity in activities if activity['timestamp_utc'].date() == max_timestamp.date() and is_active(activity['timestamp_utc'], *business_hours_data.get(store_id, ("00:00:00", "23:59:59"))) and activity['status'] != 'active')

        start_time, end_time = business_hours_data.get(store_id, ("00:00:00", "23:59:59"))
        business_hours_minutes = (datetime.strptime(end_time, '%H:%M:%S').hour - datetime.strptime(start_time, '%H:%M:%S').hour) * 60

        max_day = max(bh.day for bh in session.query(BusinessHours).filter_by(store_id=store_id).all()) if session.query(BusinessHours).filter_by(store_id=store_id).count() > 0 else 6

        uptime_last_day_duration = uptime_last_day / 60 * business_hours_minutes
        downtime_last_day_duration = downtime_last_day / 60 * business_hours_minutes

        if uptime_last_hour > 60:
            uptime_last_hour = 60 - downtime_last_hour
        if downtime_last_hour > 60:
            downtime_last_hour = 60 - uptime_last_hour

        uptime_last_hour = min(uptime_last_hour, uptime_last_day_duration)
        downtime_last_hour = min(downtime_last_hour, downtime_last_day_duration)

        uptime_last_week = uptime_last_day * 24 * (max_day + 1)
        downtime_last_week = downtime_last_day * 24 * (max_day + 1)

        final_report_data.append({
            'store_id': store_id,
            'uptime_last_hour': uptime_last_hour,
            'downtime_last_hour': downtime_last_hour,
            'uptime_last_day': uptime_last_day_duration,
            'downtime_last_day': downtime_last_day_duration,
            'uptime_last_week': uptime_last_week,
            'downtime_last_week': downtime_last_week
        })

    return final_report_data

def background_report_generation(report_id):
    timezone_data = get_timezone_data()
    business_hours_data = get_business_hours_data()
    store_activities = get_store_activities()

    report_data = generate_report_data(timezone_data, business_hours_data, store_activities)
    report_csv_path = f'report_{report_id}.csv'

    report_df = pd.DataFrame(report_data)
    report_df.to_csv(report_csv_path, index=False)

@app.route('/trigger_report', methods=['GET'])
def trigger_report():
    report_id = str(uuid.uuid4())
    threading.Thread(target=background_report_generation, args=(report_id,)).start()
    return jsonify({'report_id': report_id, 'status': 'Running'})

@app.route('/get_report', methods=['GET'])
def get_report():
    report_id = request.args.get('report_id')
    report_file = f'report_{report_id}.csv'

    if os.path.isfile(report_file):
        return send_file(report_file, as_attachment=True)
    else:
        return jsonify({'status': 'Running'})

if __name__ == '__main__':
    app.run(host='localhost', port=8000)
