import json
import boto3
import os

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('RESULTS_TABLE')

def lambda_handler(event, context):
    # Get the request ID from query parameters
    try:
        # Fix: Use correct access method for query parameters
        request_id = event.get('queryStringParameters', {}).get('requestId')
        
        if not request_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'Request ID is required'
                })
            }
        
        # Get the table
        if not table_name:
            raise ValueError("RESULTS_TABLE environment variable is not set")
            
        table = dynamodb.Table(table_name)
        
        # Query DynamoDB for the result
        response = table.get_item(
            Key={
                'request_id': request_id
            }
        )
        
        # Check if the item exists
        if 'Item' not in response:
            return {
                'statusCode': 200,  # Using 200 instead of 404 for polling
                'headers': {
                    'Access-Control-Allow-Origin': 'https://d3usydt8l24sf9.cloudfront.net',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'status': 'processing',
                    'message': 'Result not found. The calculation may still be in progress.'
                })
            }
        
        # Get the item
        item = response['Item']
        
        # Return different responses based on the status
        status = item.get('status', 'processing')
        
        if status == 'completed':
            # Fix: Convert Decimal objects to float for JSON serialization
            distance = float(item.get('distance')) if item.get('distance') else None
            
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': 'https://d3usydt8l24sf9.cloudfront.net',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'status': 'completed',
                    'request_id': request_id,
                    'distance': distance,
                    'address1': item.get('address1'),
                    'address2': item.get('address2')
                })
            }
        elif status == 'error':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': 'https://d3usydt8l24sf9.cloudfront.net',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'status': 'error',
                    'request_id': request_id,
                    'error': item.get('error', 'Unknown error')
                })
            }
        else:
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': 'https://d3usydt8l24sf9.cloudfront.net',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'status': status,
                    'request_id': request_id,
                    'message': 'Your request is being processed'
                })
            }
            
    except ValueError as ve:
        print(f"Configuration error: {str(ve)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': 'https://d3usydt8l24sf9.cloudfront.net',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Service configuration error'
            })
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': 'https://d3usydt8l24sf9.cloudfront.net',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }