#!/usr/bin/env python3
"""
MongoDB users collection fetcher with incremental support
Downloads specific user fields and supports incremental updates based on date
"""

import os
import json
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from bson import ObjectId
import argparse


def connect_to_mongodb():
    """Establish connection to MongoDB Atlas with SSL certificate"""
    
    # Connection parameters
    username = "douser"
    password = "NJuUQg62Z8i07419"
    host = "mongodb+srv://mongodb-production-d1c5b3a1.mongo.ondigitalocean.com"
    
    # Path to CA certificate
    ca_cert_path = os.path.join(os.path.dirname(__file__), "ca-certificate.crt")
    
    if not os.path.exists(ca_cert_path):
        raise FileNotFoundError(f"CA certificate file not found: {ca_cert_path}")
    
    # Connection URI
    connection_uri = f"mongodb+srv://{username}:{password}@mongodb-production-d1c5b3a1.mongo.ondigitalocean.com/admin?tls=true&tlsCAFile={ca_cert_path}"
    
    try:
        print("Connecting to MongoDB...")
        client = MongoClient(connection_uri)
        
        # Test connection
        client.admin.command('ping')
        print("Successfully connected to MongoDB!")
        
        return client
        
    except ConnectionFailure as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise
    except Exception as e:
        print(f"An error occurred: {e}")
        raise


def get_last_sync_date(metadata_file):
    """Get the last sync date from metadata file"""
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
            last_sync = metadata.get('last_sync_date')
            if last_sync:
                return datetime.fromisoformat(last_sync)
    return None


def save_metadata(metadata_file, sync_date, user_count):
    """Save sync metadata"""
    metadata = {
        'last_sync_date': sync_date.isoformat(),
        'user_count': user_count,
        'sync_timestamp': datetime.utcnow().isoformat()
    }
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)


def fetch_users(client, since_date=None):
    """Fetch users with specific fields, optionally filtered by date"""
    try:
        # Access the database and collection
        db = client["trainerday-production"]
        users_collection = db["users"]
        
        # Build query
        query = {}
        if since_date:
            query = {
                "$or": [
                    {"updatedAt": {"$gte": since_date}},
                    {"createdAt": {"$gte": since_date}}
                ]
            }
            print(f"\nFetching users updated or created since: {since_date}")
        else:
            print("\nFetching all users...")
        
        # Define fields to retrieve
        projection = {
            "_id": 1,
            "username": 1,
            "email": 1,
            "userId": 1,
            "accessLevel": 1,
            "ftp": 1,
            "createdAt": 1,
            "updatedAt": 1  # Include for incremental tracking
        }
        
        # Count total matching documents
        total_count = users_collection.count_documents(query)
        print(f"Found {total_count} users to fetch")
        
        # Fetch users with projection
        cursor = users_collection.find(query, projection)
        
        users = []
        for i, user in enumerate(cursor):
            users.append(user)
            if (i + 1) % 1000 == 0:
                print(f"Fetched {i + 1}/{total_count} users...")
        
        print(f"Retrieved {len(users)} users")
        return users
        
    except OperationFailure as e:
        print(f"Operation failed: {e}")
        raise
    except Exception as e:
        print(f"Error fetching users: {e}")
        raise


def convert_types(obj):
    """Convert MongoDB types for JSON serialization"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_types(item) for item in obj]
    else:
        return obj


def save_users_to_file(users, filename):
    """Save users data to a JSON file"""
    try:
        # Convert all users
        converted_users = [convert_types(user) for user in users]
        
        # Save to file
        with open(filename, 'w') as f:
            json.dump(converted_users, f, indent=2)
        
        print(f"\nUsers data saved to {filename}")
        
    except Exception as e:
        print(f"Error saving users to file: {e}")
        raise


def merge_users(existing_file, new_users):
    """Merge new/updated users with existing data"""
    # Load existing users
    existing_users = {}
    if os.path.exists(existing_file):
        with open(existing_file, 'r') as f:
            for user in json.load(f):
                existing_users[user['_id']] = user
    
    # Update with new/modified users
    new_count = 0
    updated_count = 0
    
    for user in new_users:
        user_id = str(user.get('_id', ''))
        if user_id in existing_users:
            updated_count += 1
        else:
            new_count += 1
        existing_users[user_id] = convert_types(user)
    
    print(f"\nMerge results: {new_count} new users, {updated_count} updated users")
    
    # Convert back to list
    return list(existing_users.values())


def main():
    """Main function to execute the script"""
    parser = argparse.ArgumentParser(description='Fetch MongoDB users with incremental support')
    parser.add_argument('--full', action='store_true', help='Perform full download (ignore last sync date)')
    parser.add_argument('--since', type=str, help='Fetch users since specific date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # File paths
    output_dir = "mongo_data"
    output_file = os.path.join(output_dir, "mongo_users.json")
    metadata_file = os.path.join(output_dir, "sync_metadata.json")
    
    try:
        # Connect to MongoDB
        client = connect_to_mongodb()
        
        # Determine sync mode
        since_date = None
        
        if args.full:
            print("\nPerforming FULL download...")
        elif args.since:
            since_date = datetime.fromisoformat(args.since)
            print(f"\nFetching users since: {since_date}")
        else:
            # Check for last sync date
            last_sync = get_last_sync_date(metadata_file)
            if last_sync:
                since_date = last_sync
                print(f"\nIncremental sync from last sync date: {since_date}")
            else:
                print("\nNo previous sync found. Performing full download...")
        
        # Record sync start time
        sync_start = datetime.utcnow()
        
        # Fetch users
        users = fetch_users(client, since_date)
        
        if since_date and os.path.exists(output_file):
            # Incremental update - merge with existing data
            print("\nMerging with existing data...")
            all_users = merge_users(output_file, users)
            save_users_to_file(all_users, output_file)
            save_metadata(metadata_file, sync_start, len(all_users))
        else:
            # Full download - replace existing file
            save_users_to_file(users, output_file)
            save_metadata(metadata_file, sync_start, len(users))
        
        # Show sample of data
        if users:
            print("\nSample user data:")
            sample = convert_types(users[0])
            # Remove updatedAt from display as it's not requested
            sample.pop('updatedAt', None)
            print(json.dumps(sample, indent=2))
        
        # Close connection
        client.close()
        print("\nConnection closed.")
        
    except Exception as e:
        print(f"\nScript failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())