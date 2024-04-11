from sqlalchemy import Column, Integer, String, Index, Time, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Timezone(Base):
    __tablename__ = 'timezone'
    id = Column(Integer, primary_key=True)
    store_id = Column(String)
    timezone_str = Column(String, default='America/Chicago')
    Index('idx_store_id_timezone', store_id)
    

class BusinessHours(Base):
    __tablename__ = 'business_hours'
    id = Column(Integer, primary_key=True)
    store_id = Column(String)
    day = Column(Integer, default=-1)
    start_time_local = Column(Time, default='00:00:00')
    end_time_local = Column(Time, default='23:59:59')
    Index('idx_store_id_business_hours', store_id)

class StoreActivity(Base):
    __tablename__ = 'store_activity'
    id = Column(Integer, primary_key=True)
    store_id = Column(String)
    status = Column(String)
    timestamp_utc = Column(DateTime)
    Index('idx_store_id_timestamp_utc', store_id, timestamp_utc)
