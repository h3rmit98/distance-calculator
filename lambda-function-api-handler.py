import json
import boto3
import os
import uuid

# Initialize SQS client
sqs = boto3.client('sqs')

QUEUE_URL = os.environ.get('QUEUE_URL')  

def lambda_handler(event, context):
    try:
        # from API Gateway
        body = json.loads(event['body'])
        
        # Extract addresses
        address1 = body.get('address1')
        address2 = body.get('address2')
        
        # Validate addresses
        if not address1 or not address2:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',  # Allow any origin for easier testing
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'Both addresses are required'
                })
            }
        
        # Generate a unique ID for this request
        request_id = str(uuid.uuid4())
        
        # Create message for SQS
        message = {
            'request_id': request_id,
            'address1': address1,
            'address2': address2
        }
        
        # Send message to SQS
        response = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        
        # Return success response to client
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': 'https://d3usydt8l24sf9.cloudfront.net',  # Allow any origin for easier testing
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Your request is being processed',
                'request_id': request_id
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': 'https://d3usydt8l24sf9.cloudfront.net',  # Allow any origin for easier testing
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }