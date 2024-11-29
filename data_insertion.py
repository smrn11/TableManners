from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import json
from data_generation import generate_all_data, CustomJSONEncoder

# MongoDB Atlas connection settings
ATLAS_URI = "mongodb+srv://jjayabas:<password>@projectcluster.lpjnc.mongodb.net/?retryWrites=true&w=majority&appName=ProjectCluster"
DB_NAME = "iot_energy_usage"

class AtlasClient ():

   def __init__ (self, atlas_uri, dbname):
       self.mongodb_client = MongoClient(atlas_uri)
       self.database = self.mongodb_client[dbname]

   ## A quick way to test if we can connect to Atlas instance
   def ping (self):
       self.mongodb_client.admin.command('ping')

   def get_collection (self, collection_name):
       collection = self.database[collection_name]
       return collection

   def find (self, collection_name, filter = {}, limit=0):
       collection = self.database[collection_name]
       items = list(collection.find(filter=filter, limit=limit))
       return items
   
   def insert_data(self, collection_name, data):
    collection = self.database[collection_name]
    if isinstance(data, list):
        result = collection.insert_many(data)
        print(f"Inserted {len(result.inserted_ids)} documents into {collection_name}")
    else:
        result = collection.insert_one(data)
        print(f"Inserted 1 document into {collection_name}")
    return result

def main():
    # Generate data
    data = generate_all_data()

    # initialize MongoDB Atlas client
    atlas_client = AtlasClient (ATLAS_URI, DB_NAME)

    # test connection
    atlas_client.ping()
    print ('Connected to Atlas instance successfully.')

    # Insert data into respective collections
    atlas_client.insert_data("cities", data["cities"])
    atlas_client.insert_data("units", data["units"])
    atlas_client.insert_data("devices", data["devices"])
    atlas_client.insert_data("energy_usage", data["energy_usage"])

    print("Data insertion complete.")

    # Print sample data from each collection
    # for collection_name in ["cities", "units", "devices", "energy_usage"]:
    #     print(f"\nSample data from {collection_name}:")
    #     sample = db[collection_name].find_one()
    #     print(json.dumps(sample, indent=2, cls=CustomJSONEncoder))

if __name__ == "__main__":
    main()
