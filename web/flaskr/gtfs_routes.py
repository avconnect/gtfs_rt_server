import json
from datetime import datetime
from pprint import pprint

import pytz
from flask import (
    Blueprint, current_app, abort, render_template, request
)

from .extensions import db
from .models import Vehicles, Feed, VehiclePosition, TripRecord, StopDistance, OccupancyStatus
from .queries import get_vehicles, vehicle_ids_to_gtfs_ids_mapped

error_log = current_app.config.get("ERROR_LOG", None)
bp = Blueprint('gtfs_routes', __name__)

MAX_PER_PAGE = 300


@bp.route('/<int:feed_id>/vehicles', methods=('GET', 'POST'))
def display_vehicles(feed_id):
    feed = db.session.query(Feed).filter_by(id=feed_id).first()
    if feed is None:
        abort(404, f"Feed id {feed_id} doesn't exist.")
    vehicles = get_vehicles(feed_id)
    return render_template('companies/vehicles.html', feed=feed, vehicles=vehicles, date=None)


@bp.route('/<int:feed_id>/summary', methods=('GET', 'POST'))
def display_vehicle_summary(feed_id):
    feed = db.session.query(Feed).filter_by(id=feed_id).first()
    if feed is None:
        abort(404, f"Feed id {feed_id} doesn't exist.")

    trip_ids = request.form.get('trip_ids', "", type=str).replace("'", "").replace(" ", "").split(',')
    requested_day = request.form.get('date', datetime.now(pytz.timezone(feed.timezone)).date(), type=str)
    page = request.form.get('page', 1, type=int)
    per_page = request.form.get('per_page', 50, type=int)
    data = db.session.query(TripRecord.vehicle_id) \
        .filter(TripRecord.trip_id.in_(trip_ids), TripRecord.day == requested_day) \
        .distinct(TripRecord.vehicle_id) \
        .paginate(page=page, per_page=per_page, max_per_page=MAX_PER_PAGE, error_out=False)
    if data.items:
        items = []
        gtfs_ids = vehicle_ids_to_gtfs_ids_mapped(feed_id)
        for v_id in data.items:
            if v_id[0] is None:
                continue
            gtfs_id = gtfs_ids.get(v_id[0], None)
            first_trip = db.session.query(TripRecord) \
                .filter(TripRecord.vehicle_id == v_id[0],
                        TripRecord.day == requested_day,
                        TripRecord.trip_id.in_(trip_ids)) \
                .order_by(TripRecord.timestamp.asc()).first()

            last_trip = db.session.query(TripRecord) \
                .filter(TripRecord.vehicle_id == v_id[0],
                        TripRecord.day == requested_day,
                        TripRecord.trip_id.in_(trip_ids)) \
                .order_by(TripRecord.timestamp.desc()).first()
            items.append(
                {'gtfs_id': gtfs_id,
                 'first_trip': first_trip.trip_id,
                 'first_trip_start': first_trip.timestamp.isoformat(),
                 'last_trip': last_trip.trip_id,
                 'last_trip_end': last_trip.timestamp.isoformat()})
        # last page add canceled trips
        if page == data.pages:
            canceled_trips = db.session.query(TripRecord) \
                .filter(TripRecord.vehicle_id == None,
                        TripRecord.day == requested_day,
                        TripRecord.trip_id.in_(trip_ids)) \
                .order_by(TripRecord.timestamp.asc()).all()
            print(f'canceled trips: {len(canceled_trips)}')
            for trip in canceled_trips:
                items.append(
                    {'vehicle_id': 'cancelled',
                     'first_trip': trip.trip_id,
                     'first_trip_start': trip.timestamp.isoformat(),
                     'last_trip': None,
                     'last_trip_start': None})
        data.items = sorted(items, key=lambda d: d['gtfs_id'])
    trip_ids_str = ','.join(trip_ids)
    return render_template('gtfs/vehicle_summary.html', feed=feed, date=requested_day, trips=trip_ids_str, data=data)


@bp.route('/<int:feed_id>/get/vehicle_position/<int:vehicle_id>', methods=('GET', 'POST'))
def get_vehicle_position(feed_id: int, vehicle_id: int):
    feed = db.session.query(Feed).filter_by(id=feed_id).first()
    if feed is None:
        abort(404, f"Feed id {feed_id} doesn't exist.")
    vehicle = db.session.query(Vehicles).filter_by(feed_id=feed_id, id=vehicle_id).first()
    if vehicle is None:
        abort(404, f"Vehicle doesn't exist.")
    requested_day = request.form.get('date', datetime.now(pytz.timezone(feed.timezone)).date(), type=str)
    page = request.form.get('page', 1, type=int)
    per_page = request.form.get('per_page', 60, type=int)

    data = db.session.query(VehiclePosition) \
        .filter_by(vehicle_id=vehicle.id, day=requested_day) \
        .order_by(VehiclePosition.timestamp.desc()) \
        .paginate(page=page, per_page=per_page, max_per_page=MAX_PER_PAGE, error_out=False)
    for i in range(len(data.items)):
        item = data.items[i].to_dict()
        item['occupancy_status'] = OccupancyStatus(item['occupancy_status']).name
        data.items[i] = item
    return render_template('gtfs/vehicle_positions.html', feed=feed, vehicle_id=vehicle.vehicle_gtfs_id,
                           date=requested_day, data=data)


@bp.route('/<int:feed_id>/get/trip_updates/<int:vehicle_id>', methods=('GET', 'POST'))
def get_vehicle_trip_updates(feed_id: id, vehicle_id: int):
    feed = db.session.query(Feed).filter_by(id=feed_id).first()
    if feed is None:
        abort(404, f"Feed id {feed_id} doesn't exist.")
    vehicle = db.session.query(Vehicles).filter_by(feed_id=feed_id, id=vehicle_id).first()
    if vehicle is None:
        abort(404, f"Vehicle doesn't exist.")
    requested_day = request.form.get('date', datetime.now(pytz.timezone(feed.timezone)).date(), type=str)
    page = request.form.get('page', 1, type=int)
    per_page = request.form.get('per_page', 60, type=int)
    data = TripRecord.query.filter_by(vehicle_id=vehicle.id, day=requested_day) \
        .order_by(TripRecord.timestamp.desc(), TripRecord.trip_id.asc()) \
        .paginate(page=page, per_page=per_page, max_per_page=MAX_PER_PAGE, error_out=False)
    for i in range(len(data.items)):
        stops = db.session.query(StopDistance) \
            .filter_by(trip_record_id=data.items[i].id) \
            .order_by(StopDistance.time_till_arrive.desc()).all()
        stops_list = [stop.to_dict() for stop in stops]
        data.items[i].stops = stops_list

    return render_template('gtfs/vehicle_trip_updates.html', feed=feed, vehicle_id=vehicle.vehicle_gtfs_id,
                           date=requested_day, data=data)


@bp.route('/<int:feed_id>/get/vehicle_position/<int:vehicle_id>/dump', methods=('GET', 'POST'))
def get_vehicle_position_dump(feed_id: int, vehicle_id: int):
    vehicle = Vehicles.query.filter_by(feed_id=feed_id, id=vehicle_id).first()
    if vehicle is None:
        abort(404, f"Vehicle doesn't exist.")

    data = db.session.query(VehiclePosition).filter_by(vehicle_id=vehicle_id) \
        .order_by(VehiclePosition.timestamp.desc()).all()

    gtfs = {"vehicle": vehicle.to_dict(), "count": len(data), "data": [d.to_dict() for d in data]}
    return json.dumps(gtfs)


@bp.route('/<int:feed_id>/get/trip_updates/<int:vehicle_id>/dump', methods=('GET', 'POST'))
def get_vehicle_trip_updates_dump(feed_id: int, vehicle_id: int):
    vehicle = Vehicles.query.filter_by(feed_id=feed_id, id=vehicle_id).first()
    if vehicle is None:
        abort(404, f"Vehicle doesn't exist.")

    data = []
    trips = TripRecord.query.filter_by(vehicle_id=vehicle_id) \
        .order_by(TripRecord.timestamp.desc()).all()
    for trip in trips:
        entry = {}
        entry.update({'trip': trip.to_dict()})
        stops = StopDistance.query.filter_by(trip_record_id=trip.id).all()
        stops_list = [stop.to_dict() for stop in stops]
        entry.update({'stops': stops_list})
        data.append(entry)

    gtfs = {"vehicle": vehicle.to_dict(), "count": len(data), "data": data}
    return json.dumps(gtfs)
