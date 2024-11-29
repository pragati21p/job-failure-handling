# Provider Configuration
provider "aws" {
  region = "us-east-1" # Adjust to your region
}

# Create an SNS Topic
resource "aws_sns_topic" "glue_failure_topic" {
  name = "glue_failure_topic"
}

# Define Email Subscribers as a List
variable "email_subscribers" {
  description = "List of email addresses to subscribe to the SNS topic"
  type        = list(string)
  default     = ["example1@example.com", "example2@example.com"] # Replace with your emails
}

# Create Subscriptions for Each Email
resource "aws_sns_topic_subscription" "email_subscribers" {
  for_each    = toset(var.email_subscribers) # Iterate over the email list
  topic_arn   = aws_sns_topic.glue_failure_topic.arn
  protocol    = "email"
  endpoint    = each.key # Each email address
}

# Create a Lambda IAM Role
resource "aws_iam_role" "lambda_role" {
  name               = "glue_failure_lambda_role"
  assume_role_policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Action : "sts:AssumeRole",
        Effect : "Allow",
        Principal : {
          Service : "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach Policies to the Lambda Role
resource "aws_iam_role_policy" "lambda_policy" {
  name   = "glue_failure_lambda_policy"
  role   = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version : "2012-10-17",
    Statement : [
      {
        Action : [
          "sns:Publish"
        ],
        Effect   : "Allow",
        Resource : aws_sns_topic.glue_failure_topic.arn
      },
      {
        Action : [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect   : "Allow",
        Resource : "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Create a Lambda Function
resource "aws_lambda_function" "glue_failure_lambda" {
  function_name = "glue_failure_notifier"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  
  # Path to the deployment package ZIP file
  filename = "${path.module}/lambda_function.zip"

  # Environment variable for SNS Topic ARN
  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.glue_failure_topic.arn,
      DB_HOST = var.DB_HOST,
      DB_PORT = var.DB_PORT,
      DB_USER = var.DB_USER,
      DB_NAME = var.DB_NAME,
      SSL_CA_PATH = var.SSL_CA_PATH
    }
  }

  # Specify the source code
  source_code_hash = filebase64sha256("${path.module}/lambda_function.zip")
}

# Create a CloudWatch Event Rule for Glue Job Failures
resource "aws_cloudwatch_event_rule" "glue_failure_rule" {
  name        = "glue_failure_rule"
  description = "Rule to trigger Lambda on Glue job failure"
  event_pattern = jsonencode({
    source      = ["aws.glue"],
    "detail-type" = ["Glue Job State Change"],
    detail      = {
      state = ["FAILED"]
    }
  })
}

# Add the Lambda Function as a Target for the CloudWatch Event Rule
resource "aws_cloudwatch_event_target" "glue_failure_target" {
  rule      = aws_cloudwatch_event_rule.glue_failure_rule.name
  target_id = "lambda_glue_failure_target"
  arn       = aws_lambda_function.glue_failure_lambda.arn
}

# Grant CloudWatch Permission to Invoke the Lambda Function
resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.glue_failure_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.glue_failure_rule.arn
}

