# from flask import Flask
import mysql.connector
from mysql.connector import pooling
import yaml, os

# Load Data from configuration file. 
mydb = dict()
mydb['host'] = os.getenv("db_host")
mydb['user'] = os.getenv("db_username")
mydb['password'] = os.getenv("db_password")

# Establish a pool of connections to MySQL database on Google Cloud Platform
try:
	connection = pooling.MySQLConnectionPool(pool_name='mypool', pool_size=5,**mydb)
	print("Successfully connected to cls-gcp-cloud-management sql Database")
except mysql.connector.Error as err:
	print("There was a problem connecting to the database: {}".format(err))
	exit()
	
# Take a connection from connection pool
def open():
	conn = connection.get_connection()
	#print("Open database connection: "+ str(conn))
	return conn

# Close connection, returning connection back to pool
def close(conn):
	#print("Close database connection: "+str(conn))
	conn.close()
