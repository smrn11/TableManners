import json
import random
from faker import Faker
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta, date
from bson import ObjectId

fake = Faker()
geolocator = Nominatim(user_agent="iot_energy_addresses")

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

# City data (pre-defined)
cities = [
    {"_id": ObjectId(), "city_name": "New York City", "state": "NY", "country": "USA", "population": 8000000},
    {"_id": ObjectId(), "city_name": "Lincoln", "state": "NE", "country": "USA", "population": 280000},
    {"_id": ObjectId(), "city_name": "San Diego", "state": "CA", "country": "USA", "population": 1400000}
]

# Define peak hours (5 PM to 9 PM)
peak_hours = range(17, 21)

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
            "_id": ObjectId(),
            "unit_id": fake.uuid4(),
            "city_id": city_info["city_name"],
            "location": location,  # GeoJSON field
            "address": address,
            "postal_code": postal_code,  # Extracted from the address
            "unit_type": random.choice(["residential", "industrial", "commercial"])
        }
        units.append(unit)
    return units

# Generate Device Collection Data
def generate_device_data(units):
    devices = []
    possible_device_types = ["smart_meter", "thermostat", "hvac"]
    possible_statuses = ["active", "inactive"]

    
    for unit in units:
        # Randomly decide how many devices to generate for this unit (1 to 3)
        num_devices = random.randint(1, 3)
        selected_device_types = random.sample(possible_device_types, num_devices)

        for device_type in selected_device_types:
            status = "active" if random.random() < 0.95 else "inactive"

            device = {
                "_id": ObjectId(),
                "device_id": fake.uuid4(),
                "unit_id": unit["unit_id"],
                "type": device_type,
                "install_date": fake.date_between(start_date="-5y", end_date="today"),
                "service_date": None if random.random() > 0.2 else fake.date_between(start_date="-1y", end_date="today"),
                "status": status
            }
            devices.append(device)
    return devices


# Generate Energy Usage Collection Data
def generate_energy_usage_data(devices, start_date, end_date):
    usage_data = []
    current_time = start_date

    while current_time <= end_date:
        for device in devices:
            is_weekend = current_time.weekday() >= 5  # 5 for Saturday, 6 for Sunday
            peak = True if current_time.hour in peak_hours and not is_weekend else False
            
            # Energy consumption logic
            energy_consumption = (
                random.uniform(5, 15) if device["type"] == "smart_meter"
                else random.uniform(0, 5)
            )
            
            usage = {
                "_id": ObjectId(),
                "device_id": device["device_id"],
                "timestamp": current_time,
                "energy_consumption_kwh": round(energy_consumption, 2),
                "peak_hours": peak
            }
            usage_data.append(usage)
        
        # Move to the next hour
        current_time += timedelta(hours=1)

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
        start_date, end_date = datetime(2024, 10, 1), datetime(2024, 11, 1)
        usage = generate_energy_usage_data(devices, start_date, end_date)
        usage_data.extend(usage)

    return {
        "cities": city_data,
        "units": units_data,
        "devices": devices_data,
        "energy_usage": usage_data
}

# Generate data
data = generate_all_data()

# print output
print("City Data:")
print(json.dumps(data["cities"], indent=4, cls=CustomJSONEncoder))
print("Unit Data:")
print(json.dumps(data["units"][:5], indent=4, cls=CustomJSONEncoder))
print("Device Data:")
print(json.dumps(data["devices"][:5], indent=4, cls=CustomJSONEncoder))
print("Device Data:")
print(json.dumps(data["energy_usage"][:5], indent=4, cls=CustomJSONEncoder))
