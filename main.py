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
client = MongoClient("mongodb+srv://jjayabas:**********@projectcluster.lpjnc.mongodb.net/?retryWrites=true&w=majority", readPreference="secondaryPreferred")
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
        pipeline = [
            {
                "$match": {
                    "city_id": city_name
                }
            },
            {
                "$lookup": {
                    "from": "devices",
                    "localField": "unit_id",
                    "foreignField": "unit_id",
                    "as": "devices"
                }
            },
            { "$unwind": "$devices" },
            {
                "$lookup": {
                    "from": "energy_usage",
                    "localField": "devices.device_id",
                    "foreignField": "device_id",
                    "as": "energy_data"
                }
            },
            { "$unwind": "$energy_data" },
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
            {
                "$group": {
                    "_id": { "city": "$city", "date": "$date", "peak_hours": "$peak_hours" },
                    "total_energy_consumption": { "$sum": "$energy_consumption_kwh" },
                    "count": { "$sum": 1 }
                }
            },
            {
                "$project": {
                    "date": "$_id.date",
                    "peak_hours": "$_id.peak_hours",
                    "total_energy_consumption": 1,
                    "average_energy_consumption": { "$divide": ["$total_energy_consumption", "$count"] }
                }
            },
            { "$sort": { "date": 1, "peak_hours": -1 } }
        ]
        
        result = list(units_collection.aggregate(pipeline))
        
        if not result:
            raise HTTPException(status_code=404, detail="City not found or no data available")
        
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
            uptime_seconds = member.get("uptime", 0)
            formatted_uptime = format_uptime(uptime_seconds)

            last_heartbeat = member.get("lastHeartbeatRecv")
            last_heartbeat = last_heartbeat.isoformat() if last_heartbeat else "Unknown"

            ping_ms = member.get("pingMs", "Unknown")

            nodes.append({
                "name": member["name"],
                "state": member["stateStr"], 
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
        pipeline = [
            {
                "$match": {
                    "city_id": city_name  
                }
            },
            {
                "$lookup": {
                    "from": "devices",
                    "localField": "unit_id",
                    "foreignField": "unit_id",
                    "as": "devices"
                }
            },
            { "$unwind": "$devices" },
            {
                "$lookup": {
                    "from": "energy_usage",
                    "localField": "devices.device_id",
                    "foreignField": "device_id",
                    "as": "energy_data"
                }
            },
            { "$unwind": "$energy_data" },
            {
                "$addFields": {
                    "postal_code": "$postal_code",
                    "timestamp": "$energy_data.timestamp",
                    "energy_consumption_kwh": "$energy_data.energy_consumption_kwh"
                }
            },
            {
                "$match": {
                    "postal_code": { "$exists": True, "$ne": None },
                    "timestamp": { "$exists": True, "$ne": None }
                }
            }
        ]

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

        pipeline += [
            {
                "$group": {
                    "_id": "$zip_code",
                    "dates": { "$push": { "date": "$date", "average_energy": "$average_energy" } },
                    "total_average_energy": { "$avg": "$average_energy" }
                }
            },
            {
                "$sort": { "total_average_energy": -1 }
            },
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

        result = list(db["units"].aggregate(pipeline))
        
        if not result:
            raise HTTPException(status_code=404, detail="No data found for the specified city or time period.")

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

    pipeline = [
        {
            "$match": {
                "city_id": request.city_name
            }
        },
        {
            "$lookup": {
                "from": "devices",
                "localField": "unit_id",
                "foreignField": "unit_id",
                "as": "devices"
            }
        },
        {"$unwind": "$devices"},
        {
            "$lookup": {
                "from": "energy_usage",
                "localField": "devices.device_id",
                "foreignField": "device_id",
                "as": "energy_data"
            }
        },
        {"$unwind": "$energy_data"},
        {
            "$match": {
                "energy_data.timestamp": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
        },
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
        {
            "$project": {
                "_id": 0,
                "date": "$_id",
                "unit_type_averages": 1
            }
        },
        {
            "$sort": {"date": 1}
        }
    ]

    try:
        results = list(db["units"].aggregate(pipeline))
        if not results:
            raise HTTPException(status_code=404, detail="No data found for the provided inputs.")
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/top-units/{city_name}")
async def get_top_units(city_name: str):
    pipeline = [
        {
            "$match": { "city_id": city_name }
        },
        {
            "$lookup": {
                "from": "devices",
                "localField": "unit_id",
                "foreignField": "unit_id",
                "as": "devices"
            }
        },
        { "$unwind": "$devices" },
        {
            "$lookup": {
                "from": "energy_usage",
                "localField": "devices.device_id",
                "foreignField": "device_id",
                "as": "energy_data"
            }
        },
        { "$unwind": "$energy_data" },
        {
            "$group": {
                "_id": "$unit_id",
                "total_energy_usage": { "$sum": "$energy_data.energy_consumption_kwh" },
                "address": { "$first": "$address" }  
            }
        },
        { "$sort": { "total_energy_usage": -1 } },
        { "$limit": 5 },
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
        results = list(db["units"].aggregate(pipeline))

        if not results:
            raise HTTPException(status_code=404, detail="No data found for the given city.")

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/average-energy-by-device-type/{city_name}")
async def get_average_energy_by_device_type(city_name: str):
    pipeline = [
        {
            "$lookup": {
                "from": "units",
                "localField": "unit_id",
                "foreignField": "unit_id",
                "as": "unit_info"
            }
        },
        { "$unwind": "$unit_info" },
        {
            "$match": { "unit_info.city_id": city_name }
        },
        {
            "$lookup": {
                "from": "energy_usage",
                "localField": "device_id",
                "foreignField": "device_id",
                "as": "energy_data"
            }
        },
        { "$unwind": "$energy_data" },
        {
            "$group": {
                "_id": "$type", 
                "average_energy_usage": { "$avg": "$energy_data.energy_consumption_kwh" }
            }
        },
        {
            "$project": {
                "_id": 0,
                "device_type": "$_id",
                "average_energy_usage": 1
            }
        }
    ]

    try:
        results = list(db["devices"].aggregate(pipeline))

        if not results:
            raise HTTPException(status_code=404, detail="No data found for the given city.")

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    

