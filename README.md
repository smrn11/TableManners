# CSE 512 Group Project by Table Manners

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
