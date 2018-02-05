provider "aws" {
	region = "${var.region}"
	access_key = "${var.access_key}"
	secret_key = "${var.secret_key}"
}

# Execute the CloudWatch rule every hour
resource "aws_cloudwatch_event_rule" "red_hat_jobs_rule" {
	name 				= "red_hat_jobs_rule"
	description 		= "Crawl the Red Hat jobs website and email new jobs."
	schedule_expression = "rate(1 hour)"	# Run hourly
}


# Apply the CloudWatch rule to a the Lambda function (i.e. the target)
resource "aws_cloudwatch_event_target" "red_hat_jobs_target" {
	target_id 	= "red_hat_jobs_target"
	rule 		= "${aws_cloudwatch_event_rule.red_hat_jobs_rule.name}"
	arn 		= "${aws_lambda_function.red_hat_jobs_lambda.arn}"
}

# Define an IAM role to execute the function under
resource "aws_iam_role" "red_hat_jobs_role" {
    name = "red_hat_jobs"
    assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

# Allow the IAM role to execute the function
resource "aws_iam_role_policy_attachment" "basic-exec-role" {
    role       = "${aws_iam_role.red_hat_jobs_role.name}"
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Allow CloudWatch to execute the lambda function
resource "aws_lambda_permission" "allow_cloudwatch" {
	statement_id 	= "AllowExecutionFromCloudWatch"
	action 			= "lambda:InvokeFunction"
	function_name 	= "${aws_lambda_function.red_hat_jobs_lambda.function_name}"
	principal 		= "events.amazonaws.com"
	source_arn 		= "${aws_cloudwatch_event_rule.red_hat_jobs_rule.arn}"
}

# And finally.. the Lambda function itself
resource "aws_lambda_function" "red_hat_jobs_lambda" {
	filename 		= "scraper.zip"
	function_name 	= "main"
	role 			= "${aws_iam_role.red_hat_jobs_role.arn}"
	handler 		= "scraper.main"
	runtime 		= "python3.6"
	timeout 		= "240"		# 4 minutes
	source_code_hash = "${base64sha256(file("scraper.zip"))}"
}
