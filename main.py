from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Literal
from pydantic import BaseModel
from datetime import datetime
from pymongo import MongoClient, errors

# FastAPI app initialization
app = FastAPI()

# Add CORS middleware to allow cross-origin requests from your frontend (localhost:3000)
origins = [
   "*" # Allow requests from your frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of origins you want to allow
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# MongoDB connection setup
client = MongoClient("mongodb+srv://jjayabas:3pfZ6qeBJC5z0mSG@projectcluster.lpjnc.mongodb.net/?retryWrites=true&w=majority", readPreference="secondaryPreferred")
db = client["iot_energy_usage"]
units_collection = db["units"]
devices_collection = db["devices"]
energy_usage_collection = db["energy_usage"]

# Request model
class EnergyUsageRequest(BaseModel):
    city_name: str
    start_date: str  # Format: "YYYY-MM-DD"
    end_date: str = None 

@app.get("/api/daily-average-energy/{city_name}", response_model=Dict[str, Dict[str, float]])
async def get_daily_average_energy_by_city(city_name: str):
    """
    Optimized Endpoint to get the daily average energy consumption during peak and off-peak hours
    for a specific city.
    """
    try:
        # Aggregation pipeline (optimized with top-down filtering)
        pipeline = [
            # Step 1: Filter units by city at the top
            {
                "$match": {
                    "city_id": city_name
                }
            },
            # Step 2: Lookup devices for these units
            {
                "$lookup": {
                    "from": "devices",
                    "localField": "unit_id",
                    "foreignField": "unit_id",
                    "as": "devices"
                }
            },
            { "$unwind": "$devices" },
            # Step 3: Lookup energy usage for these devices
            {
                "$lookup": {
                    "from": "energy_usage",
                    "localField": "devices.device_id",
                    "foreignField": "device_id",
                    "as": "energy_data"
                }
            },
            { "$unwind": "$energy_data" },
            # Step 4: Extract relevant fields and transform
            {
                "$project": {
                    "city": "$city_id",
                    "energy_consumption_kwh": "$energy_data.energy_consumption_kwh",
                    "date": {
                        "$dateToString": { "format": "%Y-%m-%d", "date": "$energy_data.timestamp" }
                    },
                    "peak_hours": "$energy_data.peak_hours"
                }
            },
            # Step 5: Group by city, date, and peak/off-peak status
            {
                "$group": {
                    "_id": { "city": "$city", "date": "$date", "peak_hours": "$peak_hours" },
                    "total_energy_consumption": { "$sum": "$energy_consumption_kwh" },
                    "count": { "$sum": 1 }
                }
            },
            # Step 6: Calculate average energy consumption
            {
                "$project": {
                    "date": "$_id.date",
                    "peak_hours": "$_id.peak_hours",
                    "total_energy_consumption": 1,
                    "average_energy_consumption": { "$divide": ["$total_energy_consumption", "$count"] }
                }
            },
            # Step 7: Sort by date and peak hours
            { "$sort": { "date": 1, "peak_hours": -1 } }
        ]
        
        # Run the aggregation pipeline
        result = list(units_collection.aggregate(pipeline))
        
        if not result:
            raise HTTPException(status_code=404, detail="City not found or no data available")
        
        # Prepare the response dictionary to hold averages for on-peak and off-peak
        response = {}

        for item in result:
            date = item["date"]
            if item["peak_hours"]:
                if date not in response:
                    response[date] = {"on_peak": 0.0, "off_peak": 0.0}
                response[date]["on_peak"] = item["average_energy_consumption"]
            else:
                if date not in response:
                    response[date] = {"on_peak": 0.0, "off_peak": 0.0}
                response[date]["off_peak"] = item["average_energy_consumption"]

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

def format_uptime(seconds):
    """
    Format uptime in D days HH:MM:SS format.
    """
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{days} days {hours:02}:{minutes:02}:{seconds:02}"

@app.get("/api/cluster-health")
async def get_cluster_health():
    """
    Check the health of the MongoDB cluster.
    """
    try:
        repl_status = client.admin.command("replSetGetStatus")
        nodes = []
        for member in repl_status.get("members", []):
            # Format uptime
            uptime_seconds = member.get("uptime", 0)
            formatted_uptime = format_uptime(uptime_seconds)

            # Get last heartbeat and ping information
            last_heartbeat = member.get("lastHeartbeatRecv")
            last_heartbeat = last_heartbeat.isoformat() if last_heartbeat else "Unknown"

            ping_ms = member.get("pingMs", "Unknown")

            nodes.append({
                "name": member["name"],
                "state": member["stateStr"],  # PRIMARY, SECONDARY, ARBITER, etc.
                "health": "healthy" if member["health"] == 1 else "unhealthy",
                "uptime": formatted_uptime,
                "last_heartbeat": last_heartbeat,
                "ping_ms": ping_ms
            })
        return {"nodes": nodes}

    except errors.ServerSelectionTimeoutError as e:
        raise HTTPException(status_code=503, detail="Unable to connect to MongoDB. Ensure a quorum is maintained.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
@app.get("/api/average-energy-zip/{city_name}/{time_period}")
async def get_average_energy_by_zip(
    city_name: str,
    time_period: Literal["day", "week", "month"]
):
    """
    Optimized Endpoint to calculate the average energy consumption per ZIP code for a specific city.
    Grouping is based on the specified time period: day, week, or month.
    ZIP codes are sorted by total average energy usage in descending order, and dates within each ZIP code
    are sorted in chronological order.
    """
    try:
        # Base pipeline: Start from city level
        pipeline = [
            # Match units by city
            {
                "$match": {
                    "city_id": city_name  # Top-down filtering by city_id
                }
            },
            # Lookup devices for units in the matched city
            {
                "$lookup": {
                    "from": "devices",
                    "localField": "unit_id",
                    "foreignField": "unit_id",
                    "as": "devices"
                }
            },
            { "$unwind": "$devices" },
            # Lookup energy usage for devices
            {
                "$lookup": {
                    "from": "energy_usage",
                    "localField": "devices.device_id",
                    "foreignField": "device_id",
                    "as": "energy_data"
                }
            },
            { "$unwind": "$energy_data" },
            # Add relevant fields for grouping
            {
                "$addFields": {
                    "postal_code": "$postal_code",
                    "timestamp": "$energy_data.timestamp",
                    "energy_consumption_kwh": "$energy_data.energy_consumption_kwh"
                }
            },
            # Exclude invalid postal codes or timestamps
            {
                "$match": {
                    "postal_code": { "$exists": True, "$ne": None },
                    "timestamp": { "$exists": True, "$ne": None }
                }
            }
        ]

        # Add time-period specific grouping and projection
        if time_period == "day":
            pipeline += [
                {
                    "$addFields": {
                        "group_date": {
                            "$dateToString": { "format": "%Y/%m/%d", "date": "$timestamp" }
                        }
                    }
                },
                {
                    "$group": {
                        "_id": { "zip_code": "$postal_code", "date": "$group_date" },
                        "total_energy": { "$sum": "$energy_consumption_kwh" },
                        "count": { "$sum": 1 }
                    }
                },
                {
                    "$project": {
                        "zip_code": "$_id.zip_code",
                        "date": "$_id.date",
                        "average_energy": { "$divide": ["$total_energy", "$count"] }
                    }
                }
            ]

        elif time_period == "week":
            pipeline += [
                {
                    "$addFields": {
                        "week_start": {
                            "$dateTrunc": {
                                "date": "$timestamp",
                                "unit": "week"
                            }
                        }
                    }
                },
                {
                    "$group": {
                        "_id": { "zip_code": "$postal_code", "week_start": "$week_start" },
                        "total_energy": { "$sum": "$energy_consumption_kwh" },
                        "count": { "$sum": 1 }
                    }
                },
                {
                    "$project": {
                        "zip_code": "$_id.zip_code",
                        "date": {
                            "$dateToString": { "format": "%Y/%m/%d", "date": "$_id.week_start" }
                        },
                        "average_energy": { "$divide": ["$total_energy", "$count"] }
                    }
                }
            ]

        elif time_period == "month":
            pipeline += [
                {
                    "$addFields": {
                        "group_date": {
                            "$dateToString": { "format": "%Y-%m", "date": "$timestamp" }
                        }
                    }
                },
                {
                    "$group": {
                        "_id": { "zip_code": "$postal_code", "date": "$group_date" },
                        "total_energy": { "$sum": "$energy_consumption_kwh" },
                        "count": { "$sum": 1 }
                    }
                },
                {
                    "$project": {
                        "zip_code": "$_id.zip_code",
                        "date": "$_id.date",
                        "average_energy": { "$divide": ["$total_energy", "$count"] }
                    }
                }
            ]

        # Add final grouping and sorting
        pipeline += [
            {
                "$group": {
                    "_id": "$zip_code",
                    "dates": { "$push": { "date": "$date", "average_energy": "$average_energy" } },
                    "total_average_energy": { "$avg": "$average_energy" }
                }
            },
            # Sort ZIP codes by total average energy usage in descending order
            {
                "$sort": { "total_average_energy": -1 }
            },
            # Ensure dates within each ZIP code are in chronological order
            {
                "$project": {
                    "_id": 0,
                    "zip_code": "$_id",
                    "dates": {
                        "$reduce": {
                            "input": { "$sortArray": { "input": "$dates", "sortBy": { "date": 1 } } },
                            "initialValue": [],
                            "in": { "$concatArrays": ["$$value", ["$$this"]] }
                        }
                    },
                    "total_average_energy": 1
                }
            }
        ]

        # Run the aggregation pipeline
        result = list(db["units"].aggregate(pipeline))
        
        if not result:
            raise HTTPException(status_code=404, detail="No data found for the specified city or time period.")

        # Format the response
        response = {}
        for entry in result:
            zip_code = entry["zip_code"]
            response[zip_code] = {
                "total_average_energy": entry["total_average_energy"],
                "dates": entry["dates"]
            }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating average energy: {str(e)}")
    
@app.post("/api/average-daily-usage-by-unit-type")
async def average_daily_usage_by_unit_type(request: EnergyUsageRequest):
# Parse start_date and end_date
    try:
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_date = (
            datetime.strptime(request.end_date, "%Y-%m-%d")
            if request.end_date
            else start_date
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use 'YYYY-MM-DD'.")

    if end_date < start_date:
        raise HTTPException(status_code=400, detail="End date cannot be earlier than start date.")

    # MongoDB aggregation pipeline
    pipeline = [
        # Step 1: Filter units by city_id
        {
            "$match": {
                "city_id": request.city_name
            }
        },
        # Step 2: Lookup devices associated with these units
        {
            "$lookup": {
                "from": "devices",
                "localField": "unit_id",
                "foreignField": "unit_id",
                "as": "devices"
            }
        },
        {"$unwind": "$devices"},
        # Step 3: Lookup energy usage readings for the filtered devices
        {
            "$lookup": {
                "from": "energy_usage",
                "localField": "devices.device_id",
                "foreignField": "device_id",
                "as": "energy_data"
            }
        },
        {"$unwind": "$energy_data"},
        # Step 4: Filter energy usage by the specified date range
        {
            "$match": {
                "energy_data.timestamp": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
        },
        # Step 5: Group by date and unit type, calculate daily averages
        {
            "$group": {
                "_id": {
                    "date": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$energy_data.timestamp"
                        }
                    },
                    "unit_type": "$unit_type"
                },
                "average_daily_usage": {"$avg": "$energy_data.energy_consumption_kwh"}
            }
        },
        # Step 6: Group results by date for easier consumption
        {
            "$group": {
                "_id": "$_id.date",
                "unit_type_averages": {
                    "$push": {
                        "unit_type": "$_id.unit_type",
                        "average_usage": "$average_daily_usage"
                    }
                }
            }
        },
        # Step 7: Project the final output
        {
            "$project": {
                "_id": 0,
                "date": "$_id",
                "unit_type_averages": 1
            }
        },
        # Step 8: Sort by date
        {
            "$sort": {"date": 1}
        }
    ]

    # Execute the pipeline
    try:
        results = list(db["units"].aggregate(pipeline))
        if not results:
            raise HTTPException(status_code=404, detail="No data found for the provided inputs.")
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/top-units/{city_name}")
async def get_top_units(city_name: str):
    # MongoDB aggregation pipeline
    pipeline = [
        # Match units for the given city
        {
            "$match": { "city_id": city_name }
        },
        # Lookup devices for the matched units
        {
            "$lookup": {
                "from": "devices",
                "localField": "unit_id",
                "foreignField": "unit_id",
                "as": "devices"
            }
        },
        { "$unwind": "$devices" },
        # Lookup energy usage for the matched devices
        {
            "$lookup": {
                "from": "energy_usage",
                "localField": "devices.device_id",
                "foreignField": "device_id",
                "as": "energy_data"
            }
        },
        { "$unwind": "$energy_data" },
        # Group by unit_id and calculate total energy usage
        {
            "$group": {
                "_id": "$unit_id",
                "total_energy_usage": { "$sum": "$energy_data.energy_consumption_kwh" },
                "address": { "$first": "$address" }  # Include the unit address
            }
        },
        # Sort by total energy usage in descending order
        { "$sort": { "total_energy_usage": -1 } },
        # Limit to the top 5 units
        { "$limit": 5 },
        # Project the results into a clean format
        {
            "$project": {
                "_id": 0,
                "unit_id": "$_id",
                "total_energy_usage": 1,
                "address": 1
            }
        }
    ]

    try:
        # Execute the pipeline
        results = list(db["units"].aggregate(pipeline))

        if not results:
            raise HTTPException(status_code=404, detail="No data found for the given city.")

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/average-energy-by-device-type/{city_name}")
async def get_average_energy_by_device_type(city_name: str):
    # MongoDB aggregation pipeline
    pipeline = [
        # Lookup units to get the city mapping
        {
            "$lookup": {
                "from": "units",
                "localField": "unit_id",
                "foreignField": "unit_id",
                "as": "unit_info"
            }
        },
        { "$unwind": "$unit_info" },
        # Match the city_name
        {
            "$match": { "unit_info.city_id": city_name }
        },
        # Lookup energy usage for devices in this city
        {
            "$lookup": {
                "from": "energy_usage",
                "localField": "device_id",
                "foreignField": "device_id",
                "as": "energy_data"
            }
        },
        { "$unwind": "$energy_data" },
        # Group by device type and calculate average energy usage
        {
            "$group": {
                "_id": "$type",  # Group by device type
                "average_energy_usage": { "$avg": "$energy_data.energy_consumption_kwh" }
            }
        },
        # Project the result in a clean format
        {
            "$project": {
                "_id": 0,
                "device_type": "$_id",
                "average_energy_usage": 1
            }
        }
    ]

    try:
        # Execute the pipeline
        results = list(db["devices"].aggregate(pipeline))

        if not results:
            raise HTTPException(status_code=404, detail="No data found for the given city.")

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    

