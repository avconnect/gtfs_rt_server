from datetime import date

from flask import Blueprint, request, jsonify
from sqlalchemy import func

from .extensions import db
from .models import Vehicles, Feed, VehiclePosition, TripRecord, StopDistance
from .queries import get_vehicle_ids, vehicle_ids_to_gtfs_ids_mapped
from .request_utils import check_get_args, check_json_post_args

bp = Blueprint('api', __name__)

FEED_ID = 'feed_id'
COMPANY_NAME = 'company_name'
GTFS_ID = 'gtfs_id'
LOCAL_DAY = 'local_day'
TRIP_IDS = 'trip_ids'


# API
@bp.route('/api/feeds', methods=['GET'])
def get_feeds():
    """
    Usage: /api/feeds
    :return: all Feeds
    """
    feeds = db.session.query(Feed).all()
    return jsonify([feed.to_dict() for feed in feeds]), 200


@bp.route('/api/feed', methods=['GET'])
def get_feed():
    """
    Usage: /api/feed/company_name=<name>
    :param: company_name: vehicle group
    :return: the feed_id for a company
    """
    data, error = check_get_args([COMPANY_NAME])
    if error:
        return jsonify(error), 400
    company_name = request.args.get(COMPANY_NAME, type=str)
    feed = db.session.query(Feed).filter_by(company_name=company_name).first()
    if feed is None:
        return jsonify({'success': False, 'message': f'company does not exist'}), 404
    return jsonify({'feed_id': feed.id}), 200


@bp.route('/api/vehicles', methods=['GET'])
def get_vehicles_gtfs_ids():
    """"
    Usage: /api/vehicles/feed_id=<id>
    :param: feed_id: integer
    :return: list of Vehicle gtfs_ids
    """
    data, error = check_get_args([FEED_ID])
    if error:
        return jsonify(error), 400
    feed_id = request.args.get(FEED_ID, type=int)
    query = db.session.query(Vehicles).filter_by(feed_id=feed_id).order_by(Vehicles.vehicle_gtfs_id.asc())
    if db.session.query(query.exists()).scalar() is False:
        return jsonify({'success': False, 'message': f'feed id does not exist'}), 404
    data = query.all()
    return jsonify({'data': [d.vehicle_gtfs_id for d in data]}), 200


@bp.route('/api/vehicle_positions', methods=['GET'])
def get_positions():
    """"
    Usage: /api/positions/feed_id=<id>&gtfs_id=<id>&local_day=<day>
    :param: feed_id: integer
    :param: gtfs_id: integer
    :param: local_day: YYYY-MM-DD iso-8601 date, local to vehicle timezone
    :return: list of VehiclePositions
    """
    data, error = check_get_args([FEED_ID, GTFS_ID, LOCAL_DAY])
    if error:
        return jsonify(error), 400
    feed_id = request.args.get(FEED_ID, type=int)
    gtfs_id = request.args.get(GTFS_ID, type=int)
    day_iso = request.args.get(LOCAL_DAY, type=str)
    local_day = date.fromisoformat(day_iso)
    vehicle = db.session.query(Vehicles).filter_by(feed_id=feed_id, vehicle_gtfs_id=gtfs_id).first()
    if vehicle is None:
        return jsonify({'success': False, 'message': f'vehicle does not exist'}), 404

    data = []
    positions = db.session.query(VehiclePosition) \
        .filter_by(vehicle_id=vehicle.id, day=local_day) \
        .order_by(VehiclePosition.timestamp.asc()).all()
    for p in positions:
        data.append({p.timestamp.isoformat(): p.to_dict()})

    return jsonify({'data': data}), 200


@bp.route('/api/trip_update/trip_ids', methods=['GET'])
def get_trip_ids():
    """"
    Usage: /api/trip_ids/feed_id=<id>&local_day=<day>
    :param: feed_id: integer
    :param: local_day: YYYY-MM-DD iso-8601 date, local to vehicle timezone
    :return: list of TripRecord trip_ids -> string
    """
    data, error = check_get_args([FEED_ID, LOCAL_DAY])
    if error:
        return jsonify(error), 400
    feed_id = request.args.get(FEED_ID, type=int)
    day_iso = request.args.get(LOCAL_DAY, type=str)
    local_day = date.fromisoformat(day_iso)
    vehicle_ids = get_vehicle_ids(feed_id)
    trips = db.session.query(TripRecord.trip_id).filter(TripRecord.vehicle_id.in_(vehicle_ids),
                                                        TripRecord.day == local_day).distinct(TripRecord.trip_id).all()

    return jsonify({'data': [trip[0] for trip in trips]}), 200


@bp.route('/api/trip_update/stops', methods=['GET'])
def get_stops():
    """"
    Usage: /api/trip_update/stops/feed_id=<id>&gtfs_id=<id>&local_day=<day>
    :param: feed_id: integer
    :param: gtfs_id: integer
    :param: local_day: YYYY-MM-DD iso-8601 date, local to vehicle timezone
    :return: list of trip_ids and stops for a vehicle
    """
    data, error = check_get_args([FEED_ID, GTFS_ID, LOCAL_DAY])
    if error:
        return jsonify(error), 400
    feed_id = request.args.get(FEED_ID, type=int)
    gtfs_id = request.args.get(GTFS_ID, type=int)
    day_iso = request.args.get(LOCAL_DAY, type=str)
    local_day = date.fromisoformat(day_iso)
    vehicle = db.session.query(Vehicles).filter_by(feed_id=feed_id, vehicle_gtfs_id=gtfs_id).first()
    if vehicle is None:
        return jsonify({'success': False, 'message': f'vehicle does not exist'}), 404

    trips = db.session.query(TripRecord).filter_by(vehicle_id=vehicle.id, day=local_day) \
        .order_by(TripRecord.time_recorded.asc()).all()
    data = []
    for trip in trips:
        stops = db.session.query(StopDistance).filter_by(trip_record_id=trip.id).all()
        if len(stops) == 0:
            continue
        stop_data = {'prev_stop': {'id': None, 'time': None}, 'next_stop': {'id': None, 'time': None}}
        for stop in stops:
            if stop.time_till_arrive > 0:
                stop_data.update({'next_stop': {'id': stop.stop_id, 'time': stop.time_till_arrive}})
            else:
                stop_data.update({'prev_stop': {'id': stop.stop_id, 'time': stop.time_till_arrive}})

        trip_data = {trip.timestamp.isoformat(): {'trip_id': trip.trip_id,
                                                  'next_stop': stop_data['next_stop'].get('id', None),
                                                  'time_to_arrival': stop_data['next_stop'].get('time', None),
                                                  'prev_stop': stop_data['prev_stop'].get('id', None),
                                                  'time_of_departure': stop_data['prev_stop'].get('time', None)
                                                  }}
        data.append(trip_data)
    return jsonify({'data': data}), 200


# format  request.post(/api/trip_update/vehicle_segments, feed_id=<>, trips_ids=[], local_day=<>)
@bp.route('/api/trip_update/vehicle_segments', methods=['POST'])
def get_trip_vehicles_segments():
    """"
    Usage: /api/stops/feed_id=<id>&gtfs_id=<id>&local_day=<day>
    :param: feed_id: integer
    :param: trip_ids: list of trip_id
    :param: local_day: YYYY-MM-DD iso-8601 date, local to vehicle timezone
    :return: dict of trip_ids and segments-> list of vehicles that ran the trip and their start and end times
    """
    data, error = check_json_post_args([FEED_ID, TRIP_IDS, LOCAL_DAY])
    if error:
        return jsonify(error), 400

    feed_id = data[FEED_ID]
    trip_ids = data[TRIP_IDS]
    day_iso = data[LOCAL_DAY]
    local_day = date.fromisoformat(day_iso)
    vehicle_ids = vehicle_ids_to_gtfs_ids_mapped(feed_id)
    vehicle_ids.update({None: None})  # canceled trips
    data = []
    for trip_id in trip_ids:
        trip_vehicles = db.session.query(TripRecord.vehicle_id,
                                         func.min(TripRecord.timestamp),
                                         func.max(TripRecord.timestamp)) \
            .filter(TripRecord.vehicle_id.in_(vehicle_ids.keys()),
                    TripRecord.trip_id == trip_id,
                    TripRecord.day == local_day) \
            .group_by(TripRecord.vehicle_id).all()
        segments = []
        for vehicle in trip_vehicles:
            gtfs_id = vehicle_ids.get(vehicle[0], None)
            first_arrived_timestamp = vehicle[1].isoformat()
            last_arrived_timestamp = vehicle[-1].isoformat()
            segments.append({'gtfs_id': gtfs_id,
                             'first_arrived_timestamp': first_arrived_timestamp,
                             'last_arrive_timestamp': last_arrived_timestamp})
        data.append({'trip_id': trip_id, 'segments': segments})
    return jsonify({'data': data}), 200
