from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from typing import Dict, Literal

# FastAPI app initialization
app = FastAPI()

# Add CORS middleware to allow cross-origin requests from your frontend (localhost:3000)
origins = [
    "http://localhost:3000",
    "http://localhost:7000"  # Allow requests from your frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of origins you want to allow
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# MongoDB connection setup
client = MongoClient("mongodb+srv://jjayabas:3pfZ6qeBJC5z0mSG@projectcluster.lpjnc.mongodb.net/")
db = client["iot_energy_usage"]
energy_usage_collection = db["energy_usage"]

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

@app.get("/api/cluster-status")
async def get_cluster_status():
    """
    Endpoint to get the active nodes in the MongoDB cluster, their status,
    and whether they are primary or secondary.
    """
    try:
        # Execute the 'replSetGetStatus' command
        repl_status = client.admin.command("replSetGetStatus")

        # Extract node information
        nodes = []
        for member in repl_status.get("members", []):
            nodes.append({
                "name": member["name"],  # Node's hostname and port
                "state": member["stateStr"],  # Node's state (e.g., PRIMARY, SECONDARY, etc.)
                "health": "healthy" if member["health"] == 1 else "unhealthy",  # Node's health
                "uptime": member.get("uptime", 0),  # Uptime in seconds
                "last_heartbeat": member.get("lastHeartbeatRecv", "N/A"),  # Last heartbeat timestamp
                "ping": member.get("pingMs", "N/A")  # Ping time in milliseconds
            })

        # Return the nodes as a JSON response
        return {"nodes": nodes}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching cluster status: {str(e)}")
    
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
