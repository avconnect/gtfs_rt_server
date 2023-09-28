import pytz
import requests

from datetime import datetime
from google.transit import gtfs_realtime_pb2
from sqlalchemy import and_

from .extensions import db, scheduler
from .logs import add_to_error_log
from .models import Vehicles, Feed, VehiclePosition, TripRecord, StopDistance
from .queries import gtfs_ids_to_vehicle_ids_mapped


def add_vehicle(feed_id: int, gtfs_id: int):
    error = None
    if feed_id is None:
        error = f"add_vehicle Error: cannot add vehicle. No feed id given: {feed_id}"
    if gtfs_id is None:
        error = f"add_vehicle Error: cannot add vehicle. No gtfs_id: {gtfs_id}"
    if error is None:
        # print(f"Attempt to add vehicle: feed: {feed_id} , gtfs: {gtfs_id}")
        vehicle = db.session.query(Vehicles).filter(
            and_(Vehicles.feed_id == feed_id, Vehicles.vehicle_gtfs_id == gtfs_id)).first()
        if vehicle is not None:
            print(f'add_vehicle Error: '
                  f'vehicle already exist for feed: {feed_id}. gtfs_id: {gtfs_id}')
            return vehicle.id, None
        else:
            vehicle = Vehicles()
            vehicle.feed_id = feed_id
            vehicle.vehicle_gtfs_id = gtfs_id
            try:
                db.session.add(vehicle)
                db.session.commit()
                return vehicle.id, None
            except BaseException as e:
                error = f"add_vehicle Error: {e}"
    return None, error


def generate_feed(url: str):
    try:
        response = requests.get(url, allow_redirects=True, verify=False, timeout=(5, None))
        response.raise_for_status()
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        return feed, None
    except BaseException as e:
        error = f'generate_feed Error: {e}'
        return None, error


def update_vehicle_position(feed_id, time_recorded=datetime.utcnow().replace(microsecond=0)):
    with scheduler.app.app_context():
        feed_data = db.session.query(Feed).filter_by(id=feed_id).first()
        url = feed_data.vehicle_position_url
        timezone = feed_data.timezone

        feed, error = generate_feed(url)
        if feed is None:
            add_to_error_log('update_vehicle_position', f'Failed to retrieve feed for {feed_id}\n{error}')
            return
        timestamp = datetime.utcfromtimestamp(feed.header.timestamp)
        target_tz = pytz.timezone(timezone)
        target_datetime = timestamp.astimezone(target_tz)
        local_date = target_datetime.date()

        gtfs_id_list = gtfs_ids_to_vehicle_ids_mapped(feed_id)
        for entity in feed.entity:
            error = None
            if not entity.HasField('vehicle'):
                continue
            if not entity.vehicle.HasField('vehicle'):
                error = f'vehicle information missing\n{entity}'
            if not entity.vehicle.HasField('position'):
                error = f'trip missing positional data\n{entity}'
            if not entity.vehicle.vehicle.id:
                error = f'vehicle id missing\n{entity}'
            if error:
                add_to_error_log('update_vehicle_position', error)
                continue
            gtfs_id = int(entity.vehicle.vehicle.id)
            if gtfs_id not in gtfs_id_list:
                vehicle_id, error = add_vehicle(feed_id, gtfs_id)
                if vehicle_id is None:
                    add_to_error_log('update_vehicle_position', f'{error}\n{entity}')
                    continue
                gtfs_id_list.update({gtfs_id: vehicle_id})
            else:
                vehicle_id = gtfs_id_list[gtfs_id]

            pos = VehiclePosition()
            pos.vehicle_id = int(vehicle_id)
            pos.lat = float(entity.vehicle.position.latitude)
            pos.lon = float(entity.vehicle.position.longitude)
            occupancy_status = entity.vehicle.occupancy_status
            pos.occupancy_status = occupancy_status if occupancy_status is not None else None
            pos.timestamp = timestamp
            pos.time_recorded = time_recorded
            pos.day = local_date
            db.session.add(pos)
        print(f'Feed: {feed_id} | {len(db.session.new)} positions added')
        db.session.commit()


def update_trip_updates(feed_id, time_recorded=datetime.utcnow().replace(microsecond=0)):
    with scheduler.app.app_context():
        feed_data = db.session.query(Feed).filter_by(id=feed_id).first()
        url = feed_data.trip_update_url
        timezone = feed_data.timezone
        feed, error = generate_feed(url)
        if feed is None:
            add_to_error_log('update_trip_updates', f'Failed to retrieve feed for {feed_id}\n{error}')
            return
        timestamp = feed.header.timestamp
        timestamp_dt = datetime.utcfromtimestamp(timestamp)
        target_tz = pytz.timezone(timezone)
        target_datetime = timestamp_dt.replace(tzinfo=pytz.UTC).astimezone(target_tz)
        local_date = target_datetime.date()

        gtfs_id_dict = gtfs_ids_to_vehicle_ids_mapped(feed_id)
        records = {}  # format v_id : [record 1, record 2, ...]
        for entity in feed.entity:
            # Get ID
            if not entity.HasField('trip_update'):
                continue
            if not entity.trip_update.HasField('trip'):
                add_to_error_log('update_trip_updates', f'no trip information found\n {entity}')
                continue
            if entity.trip_update.trip.HasField('schedule_relationship') and \
                    entity.trip_update.trip.schedule_relationship == TripRecord.CANCELED:
                # trip canceled, check if record for canceled trip already exists
                record = db.session.query(TripRecord).filter_by(vehicle_id=None,
                                                                trip_id=entity.trip_update.trip.trip_id,
                                                                day=local_date).first()
                if record is not None:
                    continue
                vehicle_id = None
            else:
                if not entity.trip_update.HasField('vehicle') or not entity.trip_update.vehicle.id:
                    '''
                    add_to_error_log('update_trip_updates',
                                     f'no gtfs_id found and trip not set to CANCELED\n {entity}')
                    vehicle_id = None
                    '''
                    continue
                else:
                    gtfs_id = int(entity.trip_update.vehicle.id)
                    if gtfs_id not in gtfs_id_dict:
                        vehicle_id, error = add_vehicle(feed_id, gtfs_id)
                        if vehicle_id is None:
                            add_to_error_log('update_trip_update', f'{error}\n{entity}')
                            continue
                        gtfs_id_dict.update({gtfs_id: vehicle_id})
                    vehicle_id = gtfs_id_dict[gtfs_id]

            # CREATE TRIP RECORD
            record = TripRecord()
            record.vehicle_id = vehicle_id
            record.trip_id = entity.trip_update.trip.trip_id
            record.timestamp = timestamp_dt
            record.time_recorded = time_recorded
            record.day = local_date
            if vehicle_id is None:
                db.session.add(record)
                continue
            if vehicle_id not in records.keys():
                records.update({vehicle_id: []})
            records[vehicle_id].append({'record': record, 'next_stop': None, 'prev_stop': None})

            # STOP TIME
            next_stop_id = None
            prev_stop_id = None
            next_stop_time = float('+inf')  # by time
            prev_stop_time = float('-inf')
            for stop in entity.trip_update.stop_time_update:
                if stop.HasField('schedule_relationship'):
                    if stop.schedule_relationship != StopDistance.SCHEDULED:
                        # stop is either skipped or no_data
                        continue
                arrival_timestamp = stop.arrival.time
                time_diff = arrival_timestamp - timestamp
                if 0 < time_diff < next_stop_time:
                    next_stop_id = stop.stop_id
                    next_stop_time = time_diff
                elif 0 >= time_diff > prev_stop_time:
                    prev_stop_id = stop.stop_id
                    prev_stop_time = time_diff
            if not next_stop_id and not prev_stop_id:
                # todo ask if to treat this case as a canceled trip
                # add_to_error_log('update_trip_updates', f'Notice: gtfs {gtfs_id} has no stops\n{entity}')
                records[vehicle_id].pop()
                record.vehicle_id = None
                db.session.add(record)
            if next_stop_id is not None:
                next_stop = StopDistance()
                next_stop.time_till_arrive = next_stop_time
                next_stop.stop_id = next_stop_id
                records[vehicle_id][-1]['next_stop'] = next_stop
            if prev_stop_id is not None:
                prev_stop = StopDistance()
                prev_stop.time_till_arrive = prev_stop_time
                prev_stop.stop_id = prev_stop_id
                records[vehicle_id][-1]['prev_stop'] = prev_stop

        num_rows_added = 0
        for vehicle in records.keys():
            curr_arrive_time = float('+inf')
            curr_record = None
            curr_next_stop = None
            curr_prev_stop = None
            for trip in records[vehicle]:
                record = trip.get('record')
                next_stop = trip.get('next_stop', None)
                prev_stop = trip.get('prev_stop', None)
                if next_stop is not None:
                    arrive_time = next_stop.time_till_arrive
                elif prev_stop is not None:
                    arrive_time = prev_stop.time_till_arrive
                else:
                    add_to_error_log('update_trip_updates', f'Notice: gtfs {gtfs_id} has no stops')
                    continue
                if (0 < arrive_time < curr_arrive_time) \
                        or (curr_arrive_time <= 0 < arrive_time) \
                        or (curr_arrive_time < arrive_time <= 0):
                    curr_arrive_time = arrive_time
                    curr_record = record
                    curr_next_stop = next_stop
                    curr_prev_stop = prev_stop
            if curr_record:
                db.session.add(curr_record)
                num_rows_added += len(db.session.new)
                db.session.flush()
                if curr_next_stop:
                    curr_next_stop.trip_record_id = curr_record.id
                    db.session.add(curr_next_stop)
                if curr_prev_stop:
                    curr_prev_stop.trip_record_id = curr_record.id
                    db.session.add(curr_prev_stop)
        num_rows_added += len(db.session.new)
        print(f'Feed: {feed_id} | {num_rows_added} trips/stops added')
        db.session.commit()
