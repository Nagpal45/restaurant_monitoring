from flask import Flask, request, jsonify, send_file
from models import Base, Timezone, BusinessHours, StoreActivity
from dbConnect import engine, session
from datetime import datetime, timedelta
import pytz
import pandas as pd
import uuid
import os

app = Flask(__name__)

Base.metadata.create_all(engine)

@app.route("/")
def index():
    return "Hello World"

def convert_to_local_time(timestamp_utc, timezone_dict, store_id):
    timezone_str = timezone_dict.get(store_id, 'America/Chicago')
    timezone = pytz.timezone(timezone_str)
    timestamp_local = timestamp_utc.astimezone(timezone)
    return timestamp_local

def get_timezone_offset(timezone_str):
    tz = pytz.timezone(timezone_str)
    now = datetime.now()
    offset = tz.utcoffset(now)
    return offset.total_seconds() / 3600

def generate_report_data():
    try:
        timezone_data = {tz.store_id: tz.timezone_str for tz in session.query(Timezone).all()}
    except Exception as e:
        print(f"Error fetching timezone data: {e}")
        return []

    try:
        business_hours_data = {bh.store_id: (bh.start_time_local.strftime('%H:%M:%S'), bh.end_time_local.strftime('%H:%M:%S')) for bh in session.query(BusinessHours).all()}
    except Exception as e:
        print(f"Error fetching business hours data: {e}")
        return []

    store_activities = session.query(StoreActivity).all()

    report_data = []
    for activity in store_activities:
        offset_hours = get_timezone_offset(timezone_data.get(activity.store_id, 'America/Chicago'))
        timestamp_local = activity.timestamp_utc + timedelta(hours=offset_hours)
        timestamp_local_truncated = timestamp_local.replace(microsecond=0)
        activity_time = timestamp_local_truncated.time()
        store_id = activity.store_id

        if business_hours_data.get(store_id):
            start_time, end_time = business_hours_data[store_id]
        else:
            start_time = "00:00:00"
            end_time = "23:59:59"
        if start_time <= activity_time.strftime('%H:%M:%S') <= end_time:
            if activity.status == 'active':
                report_data.append({'store_id': store_id, 'timestamp_utc': activity.timestamp_utc, 'status': 'active'})
            else:
                report_data.append({'store_id': store_id, 'timestamp_utc': activity.timestamp_utc, 'status': 'not active'})
    print(report_data)

    final_report_data = []
    for store_id in set(data['store_id'] for data in report_data):
        uptime_last_hour = 0
        downtime_last_hour = 0
        uptime_last_day = 0
        downtime_last_day = 0
        uptime_last_day_duration = 0
        downtime_last_day_duration = 0

        store_activities = [activity for activity in report_data if activity['store_id'] == store_id]

        for activity in store_activities:
            if activity['timestamp_utc'].hour == datetime.now().hour:
                if activity['status'] == 'active':
                    uptime_last_hour += 1
                else:
                    downtime_last_hour += 1

        uptime_last_hour_duration = uptime_last_hour * 60
        downtime_last_hour_duration = downtime_last_hour * 60

        if business_hours_data.get(store_id):
            start_time, end_time = business_hours_data[store_id]
            business_hours_minutes = (datetime.strptime(end_time, '%H:%M:%S').hour - datetime.strptime(start_time, '%H:%M:%S').hour) * 60

            for activity in store_activities:
                activity_date = activity['timestamp_utc'].date()
                if activity_date == datetime.now().date():
                    activity_time = activity['timestamp_utc'].replace(microsecond=0).time()
                    if start_time <= activity_time.strftime('%H:%M:%S') <= end_time:
                        if activity['status'] == 'active':
                            uptime_last_day += 1
                        else:
                            downtime_last_day += 1

            uptime_last_day_duration = (uptime_last_day / 60) * business_hours_minutes
            downtime_last_day_duration = (downtime_last_day / 60) * business_hours_minutes

        uptime_last_week = uptime_last_day * 24 * 7
        downtime_last_week = downtime_last_day * 24 * 7

        final_report_data.append({
            'store_id': store_id,
            'uptime_last_hour': uptime_last_hour_duration,
            'downtime_last_hour': downtime_last_hour_duration,
            'uptime_last_day': uptime_last_day_duration,
            'downtime_last_day': downtime_last_day_duration,
            'uptime_last_week': uptime_last_week,
            'downtime_last_week': downtime_last_week
        })
        print(f"Report Data (store_id: {store_id}):")
        print(f"  Uptime Last Hour: {uptime_last_hour_duration} minutes")
        print(f"  Downtime Last Hour: {downtime_last_hour_duration} minutes")
        print(f"  Uptime Last Day: {uptime_last_day_duration} minutes")
        print(f"  Downtime Last Day: {downtime_last_day_duration} minutes")
        print(f"  Uptime Last Week: {uptime_last_week} minutes")
        print(f"  Downtime Last Week: {downtime_last_week} minutes")

    return final_report_data

@app.route('/trigger_report', methods=['POST'])
def trigger_report():
    report_data = generate_report_data()
    report_id = str(uuid.uuid4())
    report_csv_path = f'report_{report_id}.csv'

    report_df = pd.DataFrame(report_data)
    report_df.to_csv(report_csv_path, index=False)

    session.close()

    return jsonify({
        'report_id': report_id,
        'status': 'Completed',
        'report_data': report_data
    })

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
