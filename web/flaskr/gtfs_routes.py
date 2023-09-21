import json

from flask import (
    Blueprint, current_app, abort, render_template, request
)

from .extensions import db
from .models import Vehicles, Feed, VehiclePosition, TripRecord, StopDistance, OccupancyStatus
from .queries import get_vehicles, get_feed_timezone

from datetime import datetime
import pytz

error_log = current_app.config.get("ERROR_LOG", None)
bp = Blueprint('gtfs_routes', __name__)


@bp.route('/<int:feed_id>/vehicles', methods=('GET', 'POST'))
def display_vehicles(feed_id):
    feed = db.session.query(Feed).filter_by(id=feed_id).first()
    if feed is None:
        abort(404, f"Feed id {feed_id} doesn't exist.")
    vehicles = get_vehicles(feed_id)
    if request.method == 'POST':
        trip_ids = (request.form['summary_trip_ids']).replace("'", "").replace(" ", "").split(',')
        date = str(request.form['summary_date'])
        print(trip_ids, date)
        data = []

        for vehicle in vehicles:
            first_trip = db.session.query(TripRecord) \
                .filter(TripRecord.vehicle_id == vehicle.id,
                        TripRecord.day == date,
                        TripRecord.trip_id.in_(trip_ids)) \
                .order_by(TripRecord.timestamp.asc()).first()
            last_trip = db.session.query(TripRecord) \
                .filter(TripRecord.vehicle_id == vehicle.id,
                        TripRecord.day == date,
                        TripRecord.trip_id.in_(trip_ids)) \
                .order_by(TripRecord.timestamp.desc()).first()
            if first_trip is None:  # then last trip is also none
                continue
            data.append(
                {'vehicle_id': vehicle.vehicle_gtfs_id,
                 'first_trip': first_trip.trip_id,
                 'first_trip_start': first_trip.timestamp.isoformat(),
                 'last_trip': last_trip.trip_id,
                 'last_trip_start': last_trip.timestamp.isoformat()})

        canceled_trips = db.session.query(TripRecord) \
            .filter(TripRecord.vehicle_id == None,
                    TripRecord.day == date,
                    TripRecord.trip_id.in_(trip_ids)) \
            .order_by(TripRecord.timestamp.asc()).all()
        print(f'canceled trips: {len(canceled_trips)}')
        for trip in canceled_trips:
            first_trip = trip.to_dict()
            data.append(
                {'vehicle_id': 'cancelled',
                 'first_trip': first_trip['trip_id'],
                 'first_trip_start': first_trip['timestamp'],
                 'last_trip': None,
                 'last_trip_start': None})
        return render_template('gtfs/vehicle_summary.html', feed=feed, date=date, data=data)
    return render_template('companies/vehicles.html', feed=feed, vehicles=vehicles, date=None)


@bp.route('/<int:feed_id>/get/vehicle_position/<int:vehicle_id>', methods=('GET', 'POST'))
def get_vehicle_position(feed_id: int, vehicle_id: int):
    vehicle = Vehicles.query.filter_by(id=vehicle_id).first()

    requested_day = None
    if request.method == 'POST':
        requested_day = str(request.form['request_date'])
    else:
        timezone = db.session.query(Feed.timezone).filter_by(id=feed_id).first()
        print(timezone)
        if len(timezone) > 0:
            tz = pytz.timezone(timezone[0])
            requested_day = datetime.now(tz).date()

    positions = VehiclePosition.query.filter_by(vehicle_id=vehicle.id, day=requested_day) \
        .order_by(VehiclePosition.timestamp.desc()).all()
    data = []
    for position in positions:
        entry = position.to_dict()
        entry['occupancy_status'] = OccupancyStatus(entry['occupancy_status']).name
        data.append(entry)
    return render_template('gtfs/vehicle_positions.html', vehicle=vehicle, day=requested_day, data=data)


@bp.route('/<int:feed_id>/get/trip_updates/<int:vehicle_id>', methods=('GET', 'POST'))
def get_vehicle_trip_updates(feed_id: id, vehicle_id: int):
    vehicle = Vehicles.query.filter_by(id=vehicle_id).first()
    requested_day = None
    if request.method == 'POST':
        requested_day = str(request.form['request_date'])

    else:
        timezone = db.session.query(Feed.timezone).filter_by(id=feed_id).first()
        print(timezone)
        if len(timezone) > 0:
            tz = pytz.timezone(timezone[0])
            requested_day = datetime.now(tz).date()
    trips = TripRecord.query.filter_by(vehicle_id=vehicle.id, day=requested_day) \
        .order_by(TripRecord.timestamp.desc(), TripRecord.trip_id.asc()).all()
    data = []
    for trip in trips:
        entry = {}
        entry.update({'trip': trip.to_dict()})
        stops = StopDistance.query.filter_by(trip_record_id=trip.id).all()
        stops_list = [stop.to_dict() for stop in stops]
        entry.update({'stops': stops_list})
        data.append(entry)

    return render_template('gtfs/vehicle_trip_updates.html', vehicle=vehicle, day=requested_day, data=data)


@bp.route('/<int:feed_id>/get/vehicle_position/<int:vehicle_id>/dump', methods=('GET', 'POST'))
def get_vehicle_position_dump(feed_id: int, vehicle_id: int):
    vehicle = Vehicles.query.filter_by(id=vehicle_id).first()
    if vehicle is None:
        abort(404, f"Vehicle doesn't exist.")

    data = db.session.query(VehiclePosition).filter_by(vehicle_id=vehicle_id) \
        .order_by(VehiclePosition.timestamp.desc()).all()

    gtfs = {"vehicle": vehicle.to_dict(), "count": len(data), "data": [d.to_dict() for d in data]}
    return json.dumps(gtfs)


@bp.route('/<int:feed_id>/get/trip_updates/<int:vehicle_id>/dump', methods=('GET', 'POST'))
def get_vehicle_trip_updates_dump(feed_id: int, vehicle_id: int):
    vehicle = Vehicles.query.filter_by(id=vehicle_id).first()
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
