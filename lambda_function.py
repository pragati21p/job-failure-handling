import boto3
import os
import json
import pymysql

# Initialize AWS clients
sns_client = boto3.client('sns')

# Database connection parameters (use environment variables for security)
DB_HOST = os.environ['DB_HOST']
DB_PORT = int(os.environ.get('DB_PORT', 6150))
DB_USER = os.environ['DB_USER']
SSL_CA_PATH = os.environ['SSL_CA_PATH']
DB_NAME = os.environ['DB_NAME']

def log_to_db(glue_job_name, job_run_id, error_message):
    """
    Logs Glue job failure details to the audit logs table in the database.
    """
    connection = None
    try:

        rds_client = boto3.client('rds', region_name=region)

        # Generate a temporary password
        DB_PASSWORD = rds_client.generate_db_auth_token(
            DBHostname=endpoint,
            Port=port,
            DBUsername=db_user
        )

        # Connect to the database
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
            ssl={"ca": SSL_CA_PATH},
            connect_timeout=60
        )
        
        # Insert failure details into the audit logs table
        with connection.cursor() as cursor:
            query = """
            INSERT INTO audit_logs (job_name, job_run_id, error_message, event_time)
            VALUES (%s, %s, %s, NOW())
            """
            cursor.execute(query, (glue_job_name, job_run_id, error_message))
        connection.commit()
        print("Successfully logged job failure to the database.")
    except Exception as e:
        print(f"Error logging to the database: {e}")
    finally:
        if connection:
            connection.close()

def lambda_handler(event, context):
    # Retrieve SNS topic ARN from environment variables
    sns_topic_arn = os.environ['SNS_TOPIC_ARN']
    
    # Extract job details from the Glue event
    glue_job_name = event['detail']['jobName']
    job_run_id = event['detail']['jobRunId']
    state = event['detail']['state']
    region = event['region']

    # Extract job arguments and error message (if available)
    job_args = event['detail'].get('arguments', {})
    error_message = event['detail'].get('errorMessage', 'No error message available.')
    
    # Check if the job failed
    if state == 'FAILED':
        # Construct the message
        subject = f"Glue Job Failure Alert: {glue_job_name}"
        message = (f"""
            The Glue job '{glue_job_name}' has failed.
            Job Run ID: {job_run_id}
            Region: {region}
            Error: {error_message}
            Division: {job_args.get('division', '-')}
            Check the CloudWatch logs for more details."""
        )
        
        try:
            # Publish the message to SNS
            response = sns_client.publish(
                TopicArn=sns_topic_arn,
                Subject=subject,
                Message=message
            )
            print(f"Message sent to SNS topic. Message ID: {response['MessageId']}")
        except Exception as e:
            print(f"Error sending message to SNS: {e}")
        
        # Log failure details to the database
        log_to_db(glue_job_name, job_run_id, error_message)
    else:
        print(f"Job state is {state}. No action required.")

    return {"statusCode": 200, "body": json.dumps("Function executed successfully.")}