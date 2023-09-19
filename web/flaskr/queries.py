from .extensions import db
from .models import Feed, Vehicles


def get_feed_timezone(feed_id):
    feed_tz = db.session.query(Feed.timezone).filter_by(id=feed_id).first()
    if feed_tz:
        return feed_tz[0]
    return None


def get_vehicles(feed_id):
    print(feed_id)
    vehicles = db.session.query(Vehicles) \
        .filter_by(feed_id=feed_id) \
        .order_by(Vehicles.vehicle_gtfs_id.asc()) \
        .all()
    return vehicles


def get_vehicle_ids(feed_id: int):
    vehicles = db.session.query(Vehicles) \
        .filter_by(feed_id=feed_id) \
        .order_by(Vehicles.vehicle_gtfs_id.asc()) \
        .all()
    return [v.id for v in vehicles]


def vehicle_id_to_gtfs_id(feed_id, vehicle_id):
    if vehicle_id is None:
        return None
    vehicle = db.session.query(Vehicles.vehicle_gtfs_id) \
        .filter_by(feed_id=feed_id, id=vehicle_id).first()
    return vehicle[0]


def gtfs_ids_to_vehicle_ids_mapped(feed_id: int):
    vehicles = db.session.query(Vehicles) \
        .filter_by(feed_id=feed_id) \
        .order_by(Vehicles.vehicle_gtfs_id.asc()) \
        .all()
    return {v.vehicle_gtfs_id: v.id for v in vehicles}


def vehicle_ids_to_gtfs_ids_mapped(feed_id: int):
    vehicles = db.session.query(Vehicles) \
        .filter_by(feed_id=feed_id) \
        .order_by(Vehicles.vehicle_gtfs_id.asc()) \
        .all()
    return {v.id: v.vehicle_gtfs_id for v in vehicles}
