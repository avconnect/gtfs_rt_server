from datetime import date, datetime

from flask import Blueprint, request, jsonify
from sqlalchemy import func, and_

from .extensions import db
from .models import Vehicles, Feed, VehiclePosition, TripRecord, StopDistance, LatestRecords
from .queries import get_vehicle_ids, vehicle_ids_to_gtfs_ids_mapped
from .request_utils import check_get_args, check_json_post_args, FEED_ID, COMPANY_NAME, GTFS_ID, DAY, TRIP_IDS

bp = Blueprint('api', __name__)


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
    company_name = request.args.get(COMPANY_NAME, type=str).lower()
    feed = db.session.query(Feed.id, Feed.timezone).filter_by(company_name=company_name).first()
    if feed is None:
        return jsonify({'success': False, 'message': f'company does not exist'}), 404
    return jsonify({'feed_id': feed[0], 'timezone': feed[1]}), 200


def get_feed_data():
    """
        Usage: /api/feed/company_name=<name>
        :param: company_name: vehicle group
        :return: the feed_id for a company
        """
    data, error = check_get_args([COMPANY_NAME])
    if error:
        return jsonify(error), 400
    company_name = request.args.get(COMPANY_NAME, type=str).lower()
    feed = db.session.query(Feed).filter_by(company_name=company_name).first()
    if feed is None:
        return jsonify({'success': False, 'message': f'company does not exist'}), 404
    return jsonify({'data': feed.to_dict()}), 200


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
    query = db.session.query(Vehicles.vehicle_gtfs_id).filter_by(feed_id=feed_id).order_by(
        Vehicles.vehicle_gtfs_id.asc())
    if db.session.query(query.exists()).scalar() is False:
        return jsonify({'success': False, 'message': f'feed id does not exist'}), 404
    data = query.all()
    return jsonify({'data': [d[0] for d in data]}), 200


@bp.route('/api/vehicle_positions', methods=['GET'])
def get_positions():
    """"
    Usage: /api/positions/feed_id=<id>&gtfs_id=<id>&day=<day>
    :param: feed_id: integer
    :param: gtfs_id: integer
    :param: day: YYYY-MM-DD iso-8601 date, local to vehicle timezone
    :return: list of VehiclePositions
    """
    data, error = check_get_args([FEED_ID, GTFS_ID, DAY])
    if error:
        return jsonify(error), 400
    feed_id = request.args.get(FEED_ID, type=int)
    gtfs_id = request.args.get(GTFS_ID, type=str)
    day_iso = request.args.get(DAY, type=str)
    day = date.fromisoformat(day_iso)
    vehicle = db.session.query(Vehicles).filter_by(feed_id=feed_id, vehicle_gtfs_id=gtfs_id).first()
    if vehicle is None:
        return jsonify({'success': False, 'message': f'vehicle does not exist'}), 404

    data = []
    positions = db.session.query(VehiclePosition) \
        .filter_by(vehicle_id=vehicle.id, day=day) \
        .order_by(VehiclePosition.timestamp.asc()).all()
    for p in positions:
        data.append({p.timestamp.isoformat(): p.to_dict()})


'''@bp.route('/api/vehicle_positions/recent/single', methods=['GET'])
def get_recent_position():
    """"
    Usage: /api/vehicle_positions/recent/single?feed_id=<id>&gtfs_id=<id>
    :param: feed_id: integer
    :param: gtfs_id: integer
    :return: Single VehiclePosition
    """
    data, error = check_get_args([FEED_ID, GTFS_ID])
    if error:
        return jsonify(error), 400
    feed_id = request.args.get(FEED_ID, type=int)
    gtfs_id = request.args.get(GTFS_ID, type=str)
    vehicle = db.session.query(Vehicles).filter_by(feed_id=feed_id, vehicle_gtfs_id=gtfs_id).first()
    if vehicle is None:
        return jsonify({'success': False, 'message': f'vehicle does not exist'}), 404

    data = []
    position = db.session.query(VehiclePosition) \
        .filter_by(vehicle_id=vehicle.id) \
        .order_by(VehiclePosition.timestamp.desc()).first()
    for p in position:
        data.append({p.timestamp.isoformat(): p.to_dict()})

    return jsonify({'data': data}), 200

'''
"SLOW"


@bp.route('/api/vehicle_positions/recent', methods=['GET'])
def get_recent_positions():
    """"
    Usage: /api/positions/recent?feed_id=<id>&gtfs_id=<id>&day=<day>
    :param: feed_id: integer
    :return: list of most recent VehiclePositions
    """
    data, error = check_get_args([FEED_ID])
    if error:
        return jsonify(error), 400
    feed_id = request.args.get(FEED_ID, type=int)
    vehicles = get_vehicle_ids(feed_id)
    query = db.session.query(VehiclePosition) \
        .join(LatestRecords,
              VehiclePosition.vehicle_id == LatestRecords.vehicle_id) \
        .filter(VehiclePosition.vehicle_id.in_(vehicles))

    # query = db.session.query(LatestRecords.vehicle_position_id).filter(LatestRecords.vehicle_id.in_(vehicles)).all()
    # position_ids = [pos[0] for pos in query]
    # positions = db.session.query(VehiclePosition).filter(VehiclePosition.vehicle_id.in_(position_ids)).all()
    positions = query.all()
    data = {}
    for p in positions:
        data.update({p.vehicle.vehicle_gtfs_id: p.to_dict()})
    return jsonify({'data': data}), 200


@bp.route('/api/trip_update/trip_ids', methods=['GET'])
def get_trip_ids():
    """"
    Usage: /api/trip_ids/feed_id=<id>&day=<day>
    :param: feed_id: integer
    :param: day: YYYY-MM-DD iso-8601 date, local to vehicle timezone
    :return: list of TripRecord trip_ids -> string
    """
    data, error = check_get_args([FEED_ID, DAY])
    if error:
        return jsonify(error), 400
    feed_id = request.args.get(FEED_ID, type=int)
    day_iso = request.args.get(DAY, type=str)
    day = date.fromisoformat(day_iso)
    vehicle_ids = get_vehicle_ids(feed_id)
    trips = db.session.query(TripRecord.trip_id) \
        .filter(TripRecord.vehicle_id.in_(vehicle_ids),
                TripRecord.day == day) \
        .distinct(TripRecord.trip_id).all()

    return jsonify({'data': [trip[0] for trip in trips]}), 200


@bp.route('/api/trip_update/stops', methods=['GET'])
def get_stops():
    """"
    Usage: /api/trip_update/stops/feed_id=<id>&gtfs_id=<id>&day=<day>
    :param: feed_id: integer
    :param: gtfs_id: string
    :param: day: YYYY-MM-DD iso-8601 date, local to vehicle timezone
    :return: list of trip_ids and stops for a vehicle
    """
    data, error = check_get_args([FEED_ID, GTFS_ID, DAY])
    if error:
        return jsonify(error), 400
    feed_id = request.args.get(FEED_ID, type=int)
    gtfs_id = request.args.get(GTFS_ID, type=str)
    day_iso = request.args.get(DAY, type=str)
    day = date.fromisoformat(day_iso)
    vehicle_id = db.session.query(Vehicles.id).filter_by(feed_id=feed_id, vehicle_gtfs_id=gtfs_id).first()
    if vehicle_id is None:
        return jsonify({'success': False, 'message': f'vehicle does not exist'}), 404

    trips = db.session.query(TripRecord) \
        .filter_by(vehicle_id=vehicle_id[0], day=day) \
        .order_by(TripRecord.timestamp.asc()).all()
    data = []
    for trip in trips:
        stops = trip.stops
        if not stops:
            continue
        stop_data = {'next_stop': {'id': None, 'time': None}, 'prev_stop': {'id': None, 'time': None}}
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


# format  request.post(/api/trip_update/vehicle_segments, feed_id=<>, trips_ids=[], day=<>)
@bp.route('/api/trip_update/vehicle_segments', methods=['POST'])
def get_trip_vehicles_segments():
    """"
    Usage: /api/trip_update/vehicle_segments/feed_id=<id>&trip_ids=<id1,id2>&day=<day>
    :param: feed_id: integer
    :param: trip_ids: list of trip_id as strings
    :param: day: YYYY-MM-DD iso-8601 date, local to vehicle timezone
    :return: dict of trip_ids and segments-> list of vehicles that ran the trip and their start and end times
    """
    data, error = check_json_post_args([FEED_ID, TRIP_IDS, DAY])
    if error:
        return jsonify(error), 400

    feed_id = int(request.json.get(FEED_ID))
    trip_ids = request.json.get(TRIP_IDS)
    day_iso = request.json.get(DAY)
    day = date.fromisoformat(day_iso)
    vehicle_ids = vehicle_ids_to_gtfs_ids_mapped(feed_id)
    data = list()
    trip_data = db.session.query(TripRecord.trip_id, TripRecord.vehicle_id,
                                 func.min(TripRecord.timestamp).label("first_timestamp"),
                                 func.max(TripRecord.timestamp).label("last_timestamp")) \
        .filter(TripRecord.vehicle_id.in_(vehicle_ids.keys()),
                TripRecord.trip_id.in_(trip_ids),
                TripRecord.day == day) \
        .group_by(TripRecord.trip_id, TripRecord.vehicle_id) \
        .order_by(TripRecord.trip_id).all()
    prev_trip_id = None
    for trip in trip_data:
        trip_id = trip[0]
        gtfs_id = vehicle_ids[trip[1]]
        first_arrive_time = trip[2].isoformat()
        last_arrive_time = trip[3].isoformat()
        if prev_trip_id == trip_id:
            data[-1]['segments'].append({
                'gtfs_id': gtfs_id,
                "first_arrive_time": first_arrive_time,
                "last_arrive_time": last_arrive_time
            })
        else:
            entry = {
                'trip_id': trip_id,
                'segments': [
                    {
                        'gtfs_id': gtfs_id,
                        "first_arrive_time": first_arrive_time,
                        "last_arrive_time": last_arrive_time
                    }
                ]
            }
            data.append(entry)
        prev_trip_id = trip_id
    return jsonify({'data': data}), 200
