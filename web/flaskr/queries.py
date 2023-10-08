from .extensions import db
from .models import Vehicles


def get_vehicles(feed_id):
    vehicles = db.session.query(Vehicles) \
        .filter_by(feed_id=feed_id) \
        .order_by(Vehicles.vehicle_gtfs_id.asc()) \
        .all()
    return vehicles


def get_vehicle_ids(feed_id: int):
    vehicle_ids = db.session.query(Vehicles.id) \
        .filter_by(feed_id=feed_id) \
        .order_by(Vehicles.vehicle_gtfs_id.asc()) \
        .all()
    if not vehicle_ids:
        return None
    return [v_id[0] for v_id in vehicle_ids]


'''def vehicle_id_to_gtfs_id(feed_id, vehicle_id):
    if vehicle_id is None:
        return None
    vehicle = db.session.query(Vehicles.vehicle_gtfs_id) \
        .filter_by(feed_id=feed_id, id=vehicle_id).first()
    return vehicle[0]
'''


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
