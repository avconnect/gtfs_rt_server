from .extensions import db
from datetime import datetime
from enum import Enum


# SCHEDULE RELATIONS
class OccupancyStatus(Enum):
    EMPTY = 0
    MANY_SEATS_AVAILABLE = 1
    FEW_SEATS_AVAILABLE = 2
    STANDING_ROOM_ONLY = 3
    CRUSHED_STANDING_ROOM_ONLY = 4
    FULL = 5
    NOT_ACCEPTING_PASSENGERS = 6
    NO_DATA_AVAILABLE = 7
    NOT_BOARDABLE = 8
    NONE = None

    @classmethod
    def _missing_(cls, value):
        return cls.NONE


class Feed(db.Model):
    __table_args__ = {'extend_existing': True}
    __tablename__ = 'gtfs_feeds'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(), unique=True, nullable=False)
    timezone = db.Column(db.String(), nullable=False)
    vehicle_position_url = db.Column(db.String(), nullable=True)
    trip_update_url = db.Column(db.String(), nullable=True)
    service_alert_url = db.Column(db.String(), nullable=True)

    def to_dict(self):
        return {'id': self.id,
                'company_name': self.company_name,
                'timezone': self.timezone,
                'trip_update_url': self.trip_update_url,
                'vehicle_position_url': self.vehicle_position_url,
                'service_alert_url': self.service_alert_url}


class Vehicles(db.Model):
    __table_args__ = {'extend_existing': True}
    __tablename__ = 'gtfs_vehicles'
    id = db.Column(db.Integer, primary_key=True)
    feed_id = db.Column(db.Integer, db.ForeignKey('gtfs_feeds.id'), nullable=False)
    vehicle_gtfs_id = db.Column(db.Integer, nullable=False)

    positions = db.relationship('VehiclePosition', backref=db.backref('vehicle', lazy='joined'))
    trips = db.relationship('TripRecord', backref=db.backref('vehicle', lazy='joined'))

    def to_dict(self):
        return {'feed_id': self.feed_id,
                'gtfs_id': self.vehicle_gtfs_id}


class VehiclePosition(db.Model):
    __table_args__ = {'extend_existing': True}
    __tablename__ = 'vehicle_position'
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("gtfs_vehicles.id"), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    occupancy_status = db.Column(db.Integer, nullable=True, default=None)
    time_recorded = db.Column(db.DateTime, nullable=False,
                              default=(datetime.utcnow()).replace(microsecond=0),
                              index=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    day = db.Column(db.Date, nullable=False, index=True)

    def to_dict(self):
        return {'lat': self.lat,
                'lon': self.lon,
                'occupancy_status': self.occupancy_status,
                'time_recorded': self.time_recorded.isoformat(),
                'timestamp': self.timestamp.isoformat(),
                'day': str(self.day)
                }

    def to_dict_ui(self):
        return {'lat': self.lat,
                'lon': self.lon,
                'occupancy_status': OccupancyStatus(self.occupancy_status).name,
                'time_recorded': self.time_recorded.isoformat(),
                'timestamp': self.timestamp.isoformat(),
                'day': str(self.day)
                }


class TripRecord(db.Model):
    __table_args__ = {'extend_existing': True}
    __tablename__ = 'trip_record'
    id = db.Column(db.Integer, primary_key=True)  # trip_record_id
    vehicle_id = db.Column(db.Integer, db.ForeignKey("gtfs_vehicles.id"), nullable=True)
    trip_id = db.Column(db.String(), nullable=False)
    time_recorded = db.Column(db.DateTime, nullable=False,
                              default=(datetime.utcnow()).replace(microsecond=0),
                              index=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    day = db.Column(db.Date, nullable=False, index=True)
    stops = db.relationship('StopDistance', backref='trip', lazy='joined')

    # scheduled relationship
    SCHEDULED = 0
    ADDED = 1
    UNSCHEDULED = 2
    CANCELED = 3

    def to_dict(self):
        return {'trip_id': self.trip_id,
                'time_recorded': self.time_recorded.isoformat(),
                'timestamp': self.timestamp.isoformat(),
                'day': str(self.day)}


class StopDistance(db.Model):
    __table_args__ = {'extend_existing': True}
    __tablename__ = 'stop_distance'
    id = db.Column(db.Integer, primary_key=True)
    trip_record_id = db.Column(db.Integer, db.ForeignKey("trip_record.id"), nullable=False)
    stop_id = db.Column(db.Integer, nullable=False)
    time_till_arrive = db.Column(db.Integer, nullable=False)

    # scheduled relationship
    SCHEDULED = 0
    SKIP = 1
    NO_DATA = 2

    def to_dict(self):
        return {'trip_record_id': self.trip_record_id,
                'stop_id': self.stop_id,
                'time_till_arrive': self.time_till_arrive}


class LatestRecords(db.Model):
    __table_args__ = {'extend_existing': True}
    __tablename__ = 'latest_records'
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("gtfs_vehicles.id"), unique=True, nullable=False)
    vehicle_position_id = db.Column(db.Integer, db.ForeignKey("vehicle_position.id"), nullable=True)
    trip_record_id = db.Column(db.Integer, db.ForeignKey("trip_record.id"), nullable=True)
