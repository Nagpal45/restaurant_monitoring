from sqlalchemy import Column, Integer, String, ForeignKey, Time, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Timezone(Base):
    __tablename__ = 'timezone'
    id = Column(Integer, primary_key=True)
    store_id = Column(String)
    timezone_str = Column(String, default='America/Chicago')

class BusinessHours(Base):
    __tablename__ = 'business_hours'
    id = Column(Integer, primary_key=True)
    store_id = Column(String)
    day = Column(Integer, default=-1)
    start_time_local = Column(Time, default='00:00:00')
    end_time_local = Column(Time, default='23:59:59')

class StoreActivity(Base):
    __tablename__ = 'store_activity'
    id = Column(Integer, primary_key=True)
    store_id = Column(String)
    status = Column(String)
    timestamp_utc = Column(DateTime)
