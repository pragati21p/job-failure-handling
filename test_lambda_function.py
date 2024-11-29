import unittest
from unittest.mock import patch, MagicMock
import json
import os
from lambda_function import lambda_handler, log_to_db

class TestLambdaFunction(unittest.TestCase):

    @patch("lambda_function.boto3.client")
    @patch("lambda_function.log_to_db")
    def test_lambda_handler_job_failure(self, mock_log_to_db, mock_boto3_client):
        # Mock environment variables
        os.environ['SNS_TOPIC_ARN'] = "arn:aws:sns:us-east-1:123456789012:glue_failure_topic"

        # Mock event
        event = {
            "detail": {
                "jobName": "test-glue-job",
                "jobRunId": "jr_12345",
                "state": "FAILED",
                "arguments": {
                    "--input-path": "s3://my-bucket/input-data/"
                },
                "errorMessage": "Test error message"
            }
        }

        # Mock SNS publish
        mock_sns_client = MagicMock()
        mock_boto3_client.return_value = mock_sns_client
        mock_sns_client.publish.return_value = {"MessageId": "test-message-id"}

        # Call the handler
        response = lambda_handler(event, None)

        # Assert SNS publish was called
        mock_sns_client.publish.assert_called_once_with(
            TopicArn="arn:aws:sns:us-east-1:123456789012:glue_failure_topic",
            Subject="Glue Job Failure Alert: test-glue-job",
            Message=unittest.mock.ANY
        )

        # Assert database logging was called
        mock_log_to_db.assert_called_once_with(
            glue_job_name="test-glue-job",
            job_run_id="jr_12345",
            error_message="Test error message"
        )

        # Assert the response
        self.assertEqual(response['statusCode'], 200)

    @patch("lambda_function.pymysql.connect")
    def test_log_to_db(self, mock_connect):
        # Mock database connection and cursor
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_connection
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        # Call the function
        log_to_db("test-glue-job", "jr_12345", "Test error message")

        # Assert that a connection was made
        mock_connect.assert_called_once_with(
            host=os.environ['DB_HOST'],
            port=int(os.environ.get('DB_PORT', 3306)),
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME']
        )

        # Assert the query was executed
        mock_cursor.execute.assert_called_once_with(
            """
            INSERT INTO audit_logs (job_name, job_run_id, error_message, event_time)
            VALUES (%s, %s, %s, NOW())
            """,
            ("test-glue-job", "jr_12345", "Test error message")
        )

        # Assert commit was called
        mock_connection.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
