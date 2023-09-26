# List of all API calls

## Get Feeds

Get a list of feeds tracked by the server

**URL** : `/api/feeds`

**Example call** :

```
http://<gtfs_server_address>/api/feeds
```

**Example output** :

```json
[
  {
    "id": 3000,
    "company_name": "name",
    "timezone": "US/Eastern",
    "vehicle_position_url": "URL or None",
    "trip_update_url": "URL or None",
    "service_alert_url": "URL or None"
  },
  {
  }
]
```

## Get Feed ID

Get the Feed ID for a company

**URL**: `/api/feed`

**Param** : `company_name: string`

**Example call** `/api/feed?company=company_a`

**Example output** :

```json
{
  "feed_id": 2302
}
```

## Get vehicle gtfs ids

Get list of all gtfs ids associated with a feed

**URL**: `/api/vehicles`

**Param** : `feed_id: int`

**Example call** `/api/vehicles?feed=<x>`

**Example output** :

```
data: {[10000, 10001, 10002, ...]}
```

## Get Vehicle Positions

Get a vehicle's positional data for a specific day

**URL**: `/api/vehicle_positions`

**Param** :

```
feed_id: int
gtfs_id: int
day: YYYY-MM-DD iso-8601 date, local to vehicle timezone
```

**Example call** `/api/vehicle_positions?feed_id=x&gtfs_id=y&day=2023-01-01`

**Example Output**

**Note** :

```
time_recorded: time when server processed data from feed. 
timestamp: timestamp contained within the feed
```

```json
{
  "data": [
    {
      "2023-09-01T12:00:00": {
        "day": "2023-09-01",
        "lat": 142.6702499389648,
        "lon": -173.7392501831055,
        "occupancy_status": 0,
        "time_recorded": "2023-09-01T12:00:00",
        "timestamp": "2023-09-01T12:00:00"
      }
    },
    {
      "2023-09-01T12:01:00": {
        "day": "2023-09-01",
        "lat": 142.6702499389648,
        "lon": -173.7392501831055,
        "occupancy_status": 1,
        "time_recorded": "2023-09-01T12:01:00",
        "timestamp": "2023-09-01T12:01:00"
      }
    }
  ]
}
```

**Valid Occupancy Statuses**

```
EMPTY = 0
MANY_SEATS_AVAILABLE = 1
FEW_SEATS_AVAILABLE = 2
STANDING_ROOM_ONLY = 3
CRUSHED_STANDING_ROOM_ONLY = 4
FULL = 5
NOT_ACCEPTING_PASSENGERS = 6
NO_DATA_AVAILABLE = 7
NOT_BOARDABLE = 8
None
```

## Get Trip Ids

Get a list of all trip ids for a specific feed on a specific day

**URL**: `/api/trip_update/trip_ids`

**Param** :

```
feed_id: int
day: YYYY-MM-DD iso-8601 date, local to vehicle timezone
```

**Example call** : `/api/trip_update/trip_ids?feed_id=x&day=2023-01-01`

**Note** : Trip Ids are always represented as strings
Example Output

```
{
  "data": [
    "485593",
    "485596",
    "485597",
    "485602",
    ...
  ]
}
```

## Get Vehicle's Trips and Stops

Get all the trips and stops for a vehicle on a specific day

**URL**: `/api/trip_update/stops`

**Param** :

```
feed_id: int
gtfs_id: int
day: YYYY-MM-DD iso-8601 date, local to vehicle timezone
```

**Example call** : `/api/trip_update/trip_ids?feed_id=x&day=2023-01-01`

**Example Output**
```
{
  "data": [
    {
      "2023-09-18T19:11:49": {
        "trip_id": "518137"
        "next_stop": 2826,
        "time_to_arrival": 150,
        "prev_stop": None,
        "time_of_departure": None,
      }
    },
    {
      "2023-09-18T19:12:49": {
        "trip_id": "518137"
        "next_stop": 2826,
        "time_to_arrival": 90,
        "prev_stop": None,
        "time_of_departure": None,
      }
    }
  ]
}
```
## Get Trip segments [POST Request]

Get all vehicles that ran a specific trip on a specific day

**URL**: `/api/trip_update/vehicle_segments`

**Param** :

```
feed_id: int
trip_id: list of trip_id:str
day: YYYY-MM-DD iso-8601 date, local to vehicle timezone
```

**Example call**: (using requests)

```
param = {
    "feed_id": "int",
    "trip_ids": "[trip_id_1,...]",
    "day": "YYYY-MM-DD"
}
requests.post(url, json=param)
```

**Example Output**

```json
{
  "data": [
    {
      "trip_id": "id_1",
      "segments": [
        {
          "gtfs_id": "1",
          "first_arrive_time": "2023-09-14T20:00:50",
          "last_arrive_time": "2023-09-14T20:08:50"
        },
        {
          "gtfs_id": "11",
          "first_arrive_time": "iso_time",
          "last_arrive_time": "iso_time"
        }
      ]
    },
    {
      "trip_id": "id_2",
      "segments": [
        {
          "gtfs_id": "2",
          "first_arrive_time": "iso_time",
          "last_arrive_time": "iso_time"
        }
      ]
    }
  ]
}
```