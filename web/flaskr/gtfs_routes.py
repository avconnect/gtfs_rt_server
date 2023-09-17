import json

from flask import (
    Blueprint, current_app, abort, render_template, redirect, request, url_for
)

from .extensions import db
from .models import Vehicles, Feed, VehiclePosition, TripRecord, StopDistance
from .queries import get_vehicles, get_vehicle_ids

error_log = current_app.config.get("ERROR_LOG", None)
bp = Blueprint('gtfs_routes', __name__)


@bp.route('/<int:feed_id>/vehicles', methods=('GET', 'POST'))
def display_vehicles(feed_id):
    feed = db.session.query(Feed).filter_by(id=feed_id).first()
    if feed is None:
        abort(404, f"Feed id {feed_id} doesn't exist.")

    vehicles = get_vehicles(feed_id)
    return render_template('companies/vehicles.html', feed_id=feed_id, company=feed.company_name,
                           timezone=feed.timezone, vehicles=vehicles)


@bp.route('/<int:feed_id>/vehicle_summaries', methods=('GET', 'POST'))
def display_vehicle_summaries(feed_id):
    # todo find way to get canceled trips
    if request.method == 'POST':
        date = str(request.form['summary_date'])
        vehicles = db.session.query(Vehicles.id, Vehicles.vehicle_gtfs_id).filter_by(feed_id=feed_id) \
            .order_by(Vehicles.vehicle_gtfs_id.asc()).all()
        vehicle_ids = [{'id': vehicle[0], 'gtfs_id': vehicle[1]} for vehicle in vehicles]
        data = []
        for v_id in vehicle_ids:
            records = db.session.query(TripRecord).filter_by(vehicle_id=v_id['id'], day=date) \
                .order_by(TripRecord.timestamp.desc()).all()
            if len(records) == 0:
                continue
            first_trip = records[-1].to_dict()
            last_trip = records[0].to_dict()
            data.append(
                {'vehicle_id': v_id['gtfs_id'],
                 'first_trip': first_trip['trip_id'],
                 'first_trip_start': first_trip['timestamp'],
                 'last_trip': last_trip['trip_id'],
                 'last_trip_start': last_trip['timestamp']})
        return render_template('gtfs/vehicle_summary.html', date=date, feed_id=feed_id, data=data)

    feed = db.session.query(Feed).filter_by(id=feed_id).first()
    vehicles = get_vehicles(feed_id)
    return redirect(url_for('companies/vehicles.html'), feed_id=feed_id, company=feed.company_name,
                    timezone=feed.timezone, vehicles=vehicles)


@bp.route('/<int:feed_id>/get/vehicle_position/<int:vehicle_id>', methods=('GET', 'POST'))
def get_vehicle_position(feed_id: int, vehicle_id: int):
    vehicle = Vehicles.query.filter_by(id=vehicle_id).first()
    positions = VehiclePosition.query.filter_by(vehicle_id=vehicle.id) \
        .order_by(VehiclePosition.timestamp.desc()).all()
    print(len(positions))
    return render_template('gtfs/vehicle_positions.html', vehicle=vehicle, data=[pos.to_dict() for pos in positions])


@bp.route('/<int:feed_id>/get/trip_updates/<int:vehicle_id>', methods=('GET', 'POST'))
def get_vehicle_trip_updates(feed_id: id, vehicle_id: int):
    vehicle = Vehicles.query.filter_by(id=vehicle_id).first()
    trips = TripRecord.query.filter_by(vehicle_id=vehicle.id) \
        .order_by(TripRecord.timestamp.desc(), TripRecord.trip_id.asc()).all()
    data = []
    for trip in trips:
        entry = {}
        entry.update({'trip': trip.to_dict()})
        stops = StopDistance.query.filter_by(trip_record_id=trip.id).all()
        stops_list = [stop.to_dict() for stop in stops]
        entry.update({'stops': stops_list})
        data.append(entry)

    print(len(trips))
    return render_template('gtfs/vehicle_trip_updates.html', vehicle=vehicle, data=data)


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
