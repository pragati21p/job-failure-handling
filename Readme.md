
### Prerequisites
1. SNS Topic: Create an SNS topic and subscribe email addresses to it.
2. Lambda IAM Role: Ensure the Lambda function has the required permissions to publish to SNS and access CloudWatch Logs.
3. Event Trigger: Configure a CloudWatch Event rule to trigger this Lambda function on Glue job failure.

> Refer modules.tf file for terraform code to create above features.

### Implementation
 
Create lambda that is triggered on AWS glue job failure. This lambda performs following tasks:
- Prepares a message to be sent
- sends an email to Amazon SNS subscribers
- logs the entry in DB table **audit_logs**

id|job_name|job_run_id|error_message|event_time
- | ------ | -------- | ----------- | --------
1|my-glue-job|jr_123456789|Exception: Data format mismatch|2024-11-29 10:15:00

> This implementation ensures failures are logged both in SNS for notifications and in the database for auditing purposes.

`Note: See test_lambda_function.py for unit tests`