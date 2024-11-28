import random
from faker import Faker
from geopy.geocoders import Nominatim
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

fake = Faker()
geolocator = Nominatim(user_agent="iot_energy_addresses")

# City data (pre-defined)
cities = [
    {"city_name": "New York City", "state": "NY", "country": "USA", "population": 8000000},
    {"city_name": "Lincoln", "state": "NE", "country": "USA", "population": 280000},
    {"city_name": "San Diego", "state": "CA", "country": "USA", "population": 1400000}
]

# Define peak hours (e.g., 5 PM to 8 PM)
peak_hours = range(17, 20)

# Helper function to generate a random address based on latitude and longitude
def get_address_and_postal_code(lat, lon):
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True)
        if location:
            address = location.address
            postal_code = location.raw.get('address', {}).get('postcode', 'Postal Code Not Found')
            return address, postal_code
        else:
            return "Address not found", "Postal Code Not Found"
    except Exception as e:
        return "Geocoder error", f"Error: {str(e)}"

# Generate City Collection Data
def generate_city_data():
    return cities

# Generate Unit Collection Data
def generate_unit_data(city_info, units_per_city=100):
    units = []
    for _ in range(10):
        lat = random.uniform(40.4774, 40.9176) if city_info["city_name"] == "New York City" else \
              random.uniform(37.6391, 37.9298) if city_info["city_name"] == "San Diego" else \
              random.uniform(40.8000, 40.9000)  # Example for Lincoln bounding box
        lon = random.uniform(-74.2591, -73.7004) if city_info["city_name"] == "New York City" else \
              random.uniform(-123.1738, -122.2818) if city_info["city_name"] == "San Diego" else \
              random.uniform(-96.7000, -96.8000)  # Example for Lincoln bounding box
        
        address, postal_code = get_address_and_postal_code(lat, lon)

        # GeoJSON location field
        location = {
            "type": "Point",
            "coordinates": [lon, lat]  # GeoJSON uses [longitude, latitude] order
        }

        unit = {
            "ID": fake.uuid4(),
            "Unit_id": fake.uuid4(),
            "City_ID": city_info["city_name"],
            "Location": location,  # GeoJSON field
            "Address": address,
            "Postal_Code": postal_code,  # Extracted from the address
            "Unit_Type": random.choice(["residential", "industrial", "commercial"])
        }
        units.append(unit)
    return units

# Generate Device Collection Data
def generate_device_data(units):
    devices = []
    for unit in units:
        # Smart Meter (primary device for each unit)
        smart_meter = {
            "ID": fake.uuid4(),
            "Device_ID": fake.uuid4(),
            "Unit_ID": unit["Unit_id"],
            "Type": "Smart Meter",
            "Install_Date": fake.date_between(start_date="-5y", end_date="today"),
            "Service_Date": None,
            "Status": "active"
        }
        devices.append(smart_meter)

        # Additional devices for the unit (e.g., thermostat, HVAC)
        for device_type in ["thermostat", "HVAC"]:
            device = {
                "ID": fake.uuid4(),
                "Device_ID": fake.uuid4(),
                "Unit_ID": unit["Unit_id"],
                "Type": device_type,
                "Install_Date": fake.date_between(start_date="-5y", end_date="today"),
                "Service_Date": None,
                "Status": "active"
            }
            devices.append(device)
    return devices

# Generate Energy Usage Collection Data
def generate_energy_usage_data(devices, start_date, end_date, readings_per_device=24):
    usage_data = []
    time_delta = (end_date - start_date).days * 24  # hourly data

    for device in devices:
        device_usage = []
        for _ in range(readings_per_device):
            timestamp = start_date + timedelta(hours=random.randint(0, time_delta))
            peak = "yes" if timestamp.hour in peak_hours else "no"
            
            # Generate energy consumption with smart meter > sum of others
            energy_consumption = random.uniform(0, 5) if device["Type"] != "Smart Meter" else \
                                 random.uniform(5, 15)
            
            usage = {
                "ID": fake.uuid4(),
                "Device_ID": device["Device_ID"],
                "Timestamp": timestamp,
                "Energy_Consumption_kwh": energy_consumption if energy_consumption > 0 else 0,
                "Peak_Hours": peak
            }
            device_usage.append(usage)

        # Ensure smart meter total > sum of other devices in the same unit
        if device["Type"] == "Smart Meter":
            total_other_devices = sum(d["Energy_Consumption_kwh"] for d in device_usage if d["Peak_Hours"] == "no")
            for usage in device_usage:
                if usage["Peak_Hours"] == "no":
                    usage["Energy_Consumption_kwh"] = max(total_other_devices + random.uniform(1, 3), usage["Energy_Consumption_kwh"])

        usage_data.extend(device_usage)
    return usage_data

# Generate all data collections
def generate_all_data():
    # Generate city data
    city_data = generate_city_data()

    # Generate unit data for each city based on population size
    units_data = []
    devices_data = []
    usage_data = []
    for city in city_data:
        units_per_city = city["population"] // 100000  # Example scale factor for unit count
        units = generate_unit_data(city, units_per_city)
        units_data.extend(units)

        # Generate devices for each unit
        devices = generate_device_data(units)
        devices_data.extend(devices)

        # Generate energy usage for each device
        start_date, end_date = datetime(2023, 1, 1), datetime(2023, 12, 31)
        usage = generate_energy_usage_data(devices, start_date, end_date, readings_per_device=24)
        usage_data.extend(usage)

    return {
        "cities": city_data,
        "units": units_data,
        "devices": devices_data,
        "energy_usage": usage_data
}

# Generate data
data = generate_all_data()

# data.write_csv("data.csv")

# write data to a json file
# with open("data_cities.json", "w") as f:
#     json.dump(data["cities"], f, indent=4)

# with open("data_units.json", "w") as f:
#     json.dump(data["units"], f, indent=4)

# with open("data_devices.json", "w") as f:
#     json.dump(data["devices"][:100], f, indent=4)

# with open("data_energy_usage.json", "w") as f:
#     json.dump(data["energy_usage"][:100], f, indent=4)

# Example output
print("City Data:", data["cities"])
print("Unit Data:")
print(json.dumps(data["units"][:10], indent=4))
# print("Device Data:", data["devices"])
# print("Energy Usage Data:", data["energy_usage"])
