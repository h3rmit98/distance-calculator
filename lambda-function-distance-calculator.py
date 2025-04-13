import json
import boto3
import os
import math
import time
from decimal import Decimal

# Initialize AWS clients
sqs = boto3.client('sqs')
location_client = boto3.client('location')
dynamodb = boto3.resource('dynamodb')

# Environment variables
PLACE_INDEX_NAME = os.environ.get('PLACE_INDEX_NAME')  # Your Amazon Location Service Place Index
TABLE_NAME = os.environ.get('RESULTS_TABLE')      # DynamoDB table for results
table = dynamodb.Table(TABLE_NAME) if TABLE_NAME else None

def lambda_handler(event, context):
    # Process SQS messages
    for record in event['Records']:
        try:
            # Parse the message body
            message_body = json.loads(record['body'])
            request_id = message_body.get('request_id')
            address1 = message_body.get('address1')
            address2 = message_body.get('address2')
            
            print(f"Processing request {request_id} for addresses: {address1} and {address2}")
            
            # Get coordinates for address1
            coords1 = geocode_address(address1)
            if not coords1:
                save_error_result(request_id, f"Could not geocode address: {address1}", address1, address2)
                continue
                
            # Get coordinates for address2
            coords2 = geocode_address(address2)
            if not coords2:
                save_error_result(request_id, f"Could not geocode address: {address2}", address1, address2)
                continue
            
            # Calculate the distance
            distance = calculate_distance(coords1, coords2)
            
            # Save the result
            save_successful_result(request_id, address1, address2, coords1, coords2, distance)
            
            print(f"Processed request {request_id}: Distance = {distance:.2f} km")
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            try:
                # Try to save the error
                message_body = json.loads(record['body'])
                request_id = message_body.get('request_id')
                address1 = message_body.get('address1')
                address2 = message_body.get('address2')
                save_error_result(request_id, f"Processing error: {str(e)}", address1, address2)
            except:
                print("Could not save error information")

def geocode_address(address):
    """Convert an address to latitude and longitude using Amazon Location Service"""
    try:
        # Call Amazon Location Service to geocode the address
        response = location_client.search_place_index_for_text(
            IndexName=PLACE_INDEX_NAME,
            Text=address,
            MaxResults=1  # We only need the top result
        )
        
        # Check if we got valid results
        if response and 'Results' in response and len(response['Results']) > 0:
            # Extract coordinates (longitude, latitude)
            place = response['Results'][0]
            coords = place['Place']['Geometry']['Point']
            
            # Amazon Location returns [longitude, latitude] but we want {lat, lng}
            return {
                'lat': coords[1],  # Latitude is second in the array
                'lng': coords[0]   # Longitude is first in the array
            }
        else:
            print(f"No geocoding results found for: {address}")
            return None
    except Exception as e:
        print(f"Geocoding error for {address}: {str(e)}")
        return None

def calculate_distance(coords1, coords2):
    """Calculate the great-circle distance between two points using the Haversine formula"""
    # Earth's radius in kilometers
    R = 6371.0
    
    # Convert latitude and longitude from degrees to radians
    lat1 = math.radians(coords1['lat'])
    lon1 = math.radians(coords1['lng'])
    lat2 = math.radians(coords2['lat'])
    lon2 = math.radians(coords2['lng'])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance

def save_successful_result(request_id, address1, address2, coords1, coords2, distance):
    """Save the successful result to DynamoDB"""
    if not table:
        print("DynamoDB table not configured, skipping result storage")
        return
        
    try:
        # Convert to Decimal for DynamoDB compatibility
        # Fix: Use 'completed' status to match the results lambda
        result = {
            'request_id': request_id,
            'status': 'completed',  # Changed from 'success' to 'completed'
            'address1': address1,
            'address2': address2,
            'coords1': {
                'lat': Decimal(str(coords1['lat'])),
                'lng': Decimal(str(coords1['lng']))
            },
            'coords2': {
                'lat': Decimal(str(coords2['lat'])),
                'lng': Decimal(str(coords2['lng']))
            },
            # Fix: Use 'distance' field name to match results lambda
            'distance': Decimal(str(distance)),  # Changed from 'distance_km'
            'timestamp': Decimal(str(int(time.time())))
        }
        
        table.put_item(Item=result)
        print(f"Saved result for request {request_id}")
    except Exception as e:
        print(f"Error saving result to DynamoDB: {str(e)}")

def save_error_result(request_id, error_message, address1=None, address2=None):
    """Save error information to DynamoDB"""
    if not table:
        print("DynamoDB table not configured, skipping error storage")
        return
        
    try:
        error_item = {
            'request_id': request_id,
            'status': 'error',
            'error': error_message,  # Changed from 'error_message' to 'error'
            'timestamp': Decimal(str(int(time.time())))
        }
        
        # Include addresses if available
        if address1:
            error_item['address1'] = address1
        if address2:
            error_item['address2'] = address2
        
        table.put_item(Item=error_item)
        print(f"Saved error for request {request_id}")
    except Exception as e:
        print(f"Error saving error info to DynamoDB: {str(e)}")