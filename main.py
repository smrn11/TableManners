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
    "http://localhost:3000",
    "http://localhost:7000",
    "http://localhost:9000" # Allow requests from your frontend
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
energy_usage_collection = db["energy_usage"]

# Request model
class EnergyUsageRequest(BaseModel):
    city_name: str
    start_date: str  # Format: "YYYY-MM-DD"
    end_date: str = None 

@app.get("/api/daily-average-energy/{city_name}", response_model=Dict[str, Dict[str, float]])
async def get_daily_average_energy_by_city(city_name: str):
    """
    Endpoint to get the daily average energy consumption during peak and off-peak hours
    for a specific city.
    """
    try:
        # Aggregation pipeline to calculate daily average on-peak vs off-peak energy consumption for a city
        pipeline = [
            {
                "$lookup": {
                    "from": "devices",
                    "localField": "device_id",
                    "foreignField": "device_id",
                    "as": "device_info"
                }
            },
            { "$unwind": "$device_info" },
            {
                "$lookup": {
                    "from": "units",
                    "localField": "device_info.unit_id",
                    "foreignField": "unit_id",
                    "as": "unit_info"
                }
            },
            { "$unwind": "$unit_info" },
            {
                "$match": {
                    "unit_info.city_id": city_name  # Filter by city name
                }
            },
            {
                "$project": {
                    "city": "$unit_info.city_id",
                    "energy_consumption_kwh": 1,
                    "date": { "$dateToString": { "format": "%Y-%m-%d", "date": "$timestamp" } },
                    "peak_hours": 1
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
        
        # Run the aggregation pipeline
        result = list(energy_usage_collection.aggregate(pipeline))
        
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
    Endpoint to calculate the average energy consumption per zip code for a specific city.
    Grouping is based on the specified time period: day, week, or month.
    """
    try:
        # Base pipeline: joins and filters
        pipeline = [
            # Join with devices collection
            {
                "$lookup": {
                    "from": "devices",
                    "localField": "device_id",
                    "foreignField": "device_id",
                    "as": "device_info"
                }
            },
            { "$unwind": "$device_info" },

            # Join with units collection
            {
                "$lookup": {
                    "from": "units",
                    "localField": "device_info.unit_id",
                    "foreignField": "unit_id",
                    "as": "unit_info"
                }
            },
            { "$unwind": "$unit_info" },

            # Filter by city name and exclude invalid postal codes or timestamps
            {
                "$match": {
                    "unit_info.city_id": city_name,
                    "unit_info.postal_code": { "$exists": True, "$ne": None },
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
                        "_id": { "zip_code": "$unit_info.postal_code", "date": "$group_date" },
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
                            "$dateSubtract": {
                                "startDate": "$timestamp",
                                "unit": "day",
                                "amount": { "$subtract": ["$dayOfWeek", 1] }
                            }
                        },
                        "week_end": {
                            "$dateAdd": {
                                "startDate": {
                                    "$dateSubtract": {
                                        "startDate": "$timestamp",
                                        "unit": "day",
                                        "amount": { "$subtract": ["$dayOfWeek", 1] }
                                    }
                                },
                                "unit": "day",
                                "amount": 6
                            }
                        }
                    }
                },
                {
                    "$group": {
                        "_id": { "zip_code": "$unit_info.postal_code", "week_start": "$week_start", "week_end": "$week_end" },
                        "total_energy": { "$sum": "$energy_consumption_kwh" },
                        "count": { "$sum": 1 }
                    }
                },
                {
                    "$project": {
                        "zip_code": "$_id.zip_code",
                        "date": {
                            "$concat": [
                                { "$dateToString": { "format": "%Y/%m/%d", "date": "$_id.week_start" } },
                                "-",
                                { "$dateToString": { "format": "%Y/%m/%d", "date": "$_id.week_end" } }
                            ]
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
                        "_id": { "zip_code": "$unit_info.postal_code", "date": "$group_date" },
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

        # Sort the results
        pipeline.append({ "$sort": { "zip_code": 1, "date": 1 } })

        # Run the aggregation pipeline
        result = list(db["energy_usage"].aggregate(pipeline))
        
        if not result:
            raise HTTPException(status_code=404, detail="No data found for the specified city or time period.")

        # Format the response
        response = {}
        for entry in result:
            zip_code = entry["zip_code"]
            date_label = entry["date"]
            avg_energy = entry["average_energy"]

            if zip_code not in response:
                response[zip_code] = []

            response[zip_code].append({"date": date_label, "average_energy": avg_energy})

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
    

