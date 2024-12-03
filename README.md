# Geo-Distributed Database for analyzing energy usage in smart cities
## A project by group Table Manners for CSE-512

As part of our project for the course CSE-512: Distributed Database Systems, we have built this application that allows user (potentially consumers and energy providers) to analyse energy consumption data originating from IOT devices in smart cities that are rapidly expanding in this day and age. To demonstrate the usefulness of this application in a real-world scenario, we have:
- Created scripts that create synthetic data that is very realistic and logically accurate (to mimic real world closeness).
- Set up 3 nodes in our MongoDB cluster (one in `us-east-1`, one in `us-east-2` and one in `us-west-1`) to harness the advantages of a distributed system like performance and fault tolerance.
- Created a front end that visualizes query results in graphs and charts to make the data analysis more easier and insightful.

To try our project, follow the steps below:

## Setting up the project

- The first step to run this project on your local is to clone this repository/downnload the ZIP file to your local machine.
- Next, ensure your `MongoDB` cluster is up and running in a healthy state. Once you've confirmed this, we will need the **connection string** to connect to the `MongoDB` cluster in the file `main.py`. It will be of the form:
  ```
  mongodb+srv://<username>:<password>@projectcluster.lpjnc.mongodb.net/
  ```
  Here replace the  `<username>` and `<password>` fields with the real values of a user who has all the necessary permissions to perform CRUD operations as well as administrator operations.
  
  Also, for this particular implementation, we need the property `readPreference` to be set to `secondaryPreferred` in the `MongoClient` initialization. The code has to be as shown below:
  ```
  client = MongoClient("<username>:<password>@projectcluster.lpjnc.mongodb.net/", readPreference="secondaryPreferred")
  ```
- Once, this change has been made to the `main.py` file, paste the connection string similarly in the `data_insertion.py` file as well. (This file connects to the cluster and just inserts the data into the database).

## Data generation and insertion

Pre-requisites: We will need the libraries `pymongo`, `Faker`, `bson` and `geopy` libraries for this part. So install them using the command: `pip install pymongo faker bson geopy`.

- Once these libraries have been installed, you can run the `data_insertion.py` similarly using the command `python data_insertion.py`, as this file will call the `data_generation.py` file during it's execution.
- If both of these python files have executed without any issues, then the database `iot_energy_usage` in your cluster will have the synthetic data that was just generated.

## Running the back-end 

Pre-requisites: We will need the libraries `fastapi`, `uvicorn`, `pymongo` (already installed above) and `pydantic` libraries for this part. So install them using the command: `pip install fastapi uvicorn pymongo pydantic`.

- As we have already pasted the connection string into the `main.py` file, all we need to do is start the FastAPI application using the command:
  ```
  uvicorn main:app --reload
  ```
  As soon as we enter this command, the backend service should automatically start on port `8000`. Now our backend service is up and running and ready to recieve REST API calls.

## Running the front-end

- For this we will need a simple `HTTP server` to serve our files, so if not installed, it can be installed using the command: `npm install -g http-server`.
- Once this is done, we just have to start the server using the command:
  ```
  python -m http.server 7000
  ```
- After the server is running without any issues, open `localhost:7000` in the browser and you will be able to interact with the dashboard and make API calls to the backend.
