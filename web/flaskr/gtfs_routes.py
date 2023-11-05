import json
from datetime import datetime

import pytz
from flask import (
    Blueprint, current_app, abort, render_template, request
)
from sqlalchemy import func, and_
from sqlalchemy.orm import aliased

from .extensions import db
from .models import Vehicles, Feed, VehiclePosition, TripRecord
from .queries import vehicle_ids_to_gtfs_ids_mapped

error_log = current_app.config.get("ERROR_LOG", None)
bp = Blueprint('gtfs_routes', __name__)

MAX_PER_PAGE = 60
PER_PAGE_DEFAULT = 10
PAGE_DEFAULT = 1


@bp.route('/<int:feed_id>/vehicles', methods=('GET', 'POST'))
def display_vehicles(feed_id):
    feed = db.session.query(Feed).filter_by(id=feed_id).first()
    if feed is None:
        abort(404, f"Feed id {feed_id} doesn't exist.")
    vehicles = db.session.query(Vehicles.id, Vehicles.vehicle_gtfs_id) \
        .filter_by(feed_id=feed_id) \
        .order_by(Vehicles.vehicle_gtfs_id).all()
    return render_template('companies/vehicles.html', feed=feed, vehicles=vehicles, date=None)


@bp.route('/<int:feed_id>/summary', methods=('GET', 'POST'))
def display_vehicle_summary(feed_id):
    feed = db.session.query(Feed).filter_by(id=feed_id).first()
    if feed is None:
        abort(404, f"Feed id {feed_id} doesn't exist.")
    trip_ids = request.form.get('trip_ids', "", type=str).replace("'", "").replace(" ", "").split(',')
    requested_day = request.form.get('date', datetime.now(pytz.timezone(feed.timezone)).date(), type=str)
    page = request.form.get('page', 1, type=int)
    per_page = request.form.get('per_page', PER_PAGE_DEFAULT, type=int)
    if request.method == "POST":
        first_trip = aliased(TripRecord)
        last_trip = aliased(TripRecord)
        vehicle_ids = vehicle_ids_to_gtfs_ids_mapped(feed_id)

        first_trip_subquery = db.session.query(
            TripRecord.vehicle_id,
            func.min(TripRecord.timestamp).label("first_timestamp")) \
            .filter(TripRecord.vehicle_id.in_(vehicle_ids),
                    TripRecord.trip_id.in_(trip_ids),
                    TripRecord.day == requested_day) \
            .group_by(TripRecord.vehicle_id).subquery()

        last_trip_subquery = db.session.query(
            TripRecord.vehicle_id,
            func.max(TripRecord.timestamp).label("last_timestamp")
        ).filter(TripRecord.vehicle_id.in_(vehicle_ids),
                 TripRecord.trip_id.in_(trip_ids),
                 TripRecord.day == requested_day)\
            .group_by(TripRecord.vehicle_id).subquery()

        data = db.session.query(first_trip_subquery.c.vehicle_id,
                                first_trip.trip_id,
                                first_trip_subquery.c.first_timestamp,
                                last_trip.trip_id,
                                last_trip_subquery.c.last_timestamp) \
            .join(last_trip_subquery, last_trip_subquery.c.vehicle_id == first_trip_subquery.c.vehicle_id) \
            .join(first_trip,
                  and_(first_trip.vehicle_id == first_trip_subquery.c.vehicle_id,
                       first_trip.timestamp == first_trip_subquery.c.first_timestamp)) \
            .join(last_trip,
                  and_(last_trip.vehicle_id == last_trip_subquery.c.vehicle_id,
                       last_trip.timestamp == last_trip_subquery.c.last_timestamp)) \
            .order_by(first_trip_subquery.c.vehicle_id.asc()) \
            .paginate(page=page,
                      per_page=per_page,
                      max_per_page=MAX_PER_PAGE,
                      error_out=False)
        if data.items:
            items = []
            for entry in data.items:
                gtfs_id = vehicle_ids.get(entry[0], None)
                items.append(
                    {'gtfs_id': gtfs_id,
                     'first_trip': entry[1],
                     'first_trip_start': entry[2].isoformat(),
                     'last_trip': entry[-2],
                     'last_trip_end': entry[-1].isoformat()})
            data.items = items
        trip_ids_str = ','.join(trip_ids)
        return render_template('gtfs/vehicle_summary.html', feed=feed, date=requested_day, trips=trip_ids_str,
                               data=data)

    return render_template('gtfs/vehicle_summary.html', feed=feed, date=requested_day, trips="", data=None)


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
    per_page = request.form.get('per_page', PER_PAGE_DEFAULT, type=int)

    data = db.session.query(VehiclePosition) \
        .filter_by(vehicle_id=vehicle.id, day=requested_day) \
        .order_by(VehiclePosition.timestamp.desc()) \
        .paginate(page=page, per_page=per_page, max_per_page=MAX_PER_PAGE, error_out=False)
    for i in range(len(data.items)):
        item = data.items[i].to_dict_ui()
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
    per_page = request.form.get('per_page', PER_PAGE_DEFAULT, type=int)
    data = db.session.query(TripRecord) \
        .filter(TripRecord.vehicle_id == vehicle.id, TripRecord.day == requested_day) \
        .order_by(TripRecord.timestamp.desc()) \
        .paginate(page=page, per_page=per_page, max_per_page=MAX_PER_PAGE, error_out=False)
    for i in range(len(data.items)):
        data.items[i].stops = sorted(data.items[i].stops, key=lambda x: x.time_till_arrive, reverse=True)
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
        stops_list = [stop.to_dict() for stop in trip.stops]
        entry.update({'stops': stops_list})
        data.append(entry)

    gtfs = {"vehicle": vehicle.to_dict(), "count": len(data), "data": data}
    return json.dumps(gtfs)
