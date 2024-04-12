from sqlalchemy.orm import sessionmaker
from models import StoreActivity, BusinessHours, Timezone
from dbConnect import engine
import csv

Session = sessionmaker(bind=engine)
session = Session()

def batch_insert_records(model_class, records):
    session.bulk_insert_mappings(model_class, records)
    session.commit()

def load_store_activity_data():
    store_activity_data = []
    with open('data/store_status.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            store_id, status, timestamp_utc = row['store_id'], row['status'], row['timestamp_utc']
            store_activity_data.append({'store_id': store_id, 'status': status, 'timestamp_utc': timestamp_utc})
            if len(store_activity_data) >= 1000:
                batch_insert_records(StoreActivity, store_activity_data)
                store_activity_data = []
    
    if store_activity_data:
        batch_insert_records(StoreActivity, store_activity_data)

def load_business_hours_data():
    business_hours_data = []
    with open('data/Menu_hours.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            store_id, day, start_time_local, end_time_local = row['store_id'], row['day'], row['start_time_local'], row['end_time_local']
            business_hours_data.append({'store_id': store_id, 'day': day, 'start_time_local': start_time_local, 'end_time_local': end_time_local})
            if len(business_hours_data) >= 1000:
                batch_insert_records(BusinessHours, business_hours_data)
                business_hours_data = []
    
    if business_hours_data:
        batch_insert_records(BusinessHours, business_hours_data)

def load_timezone_data():
    timezone_data = []
    with open('data/bq-results-20230125-202210-1674678181880.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            store_id, timezone_str = row['store_id'], row['timezone_str']
            timezone_data.append({'store_id': store_id, 'timezone_str': timezone_str})
            if len(timezone_data) >= 1000:
                batch_insert_records(Timezone, timezone_data)
                timezone_data = []
    
    if timezone_data:
        batch_insert_records(Timezone, timezone_data)

load_store_activity_data()
load_business_hours_data()
load_timezone_data()
session.close()
