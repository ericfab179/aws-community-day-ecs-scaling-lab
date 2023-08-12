# AWS Community Day - ECS Autoscaling Lab

## Prerequisites
- Pulumi
- Docker
- AWS account with programatic credentials

## Step by Step

### Configure AWS credentials
```
export AWS_ACCESS_KEY_ID=<YOUR_ACCESS_KEY_ID>
export AWS_SECRET_ACCESS_KEY=<YOUR_SECRET_ACCESS_KEY>
export AWS_REGION=<YOUR_AWS_REGION>
```

### App
The app is a simple Flask API with two enpoints, one for cpu intensive testing and other for memeory intensive operations.

### Pulumi
```
cd pulumi
pulumi plugin install resource aws v5.35.0
export PULUMI_STACK_NAME=aws_comunity_day_2023_<CUSTOM_SUFFIX>
pulumi stack init $PULUMI_STACK_NAME
export PULUMI_CONFIG_PASSPHRASE_FILE=<YOUR_FILE_WITH_PULUMI_PASSPHRASE>
pulumi preview -s $PULUMI_STACK_NAME
pulumi up -s $PULUMI_STACK_NAME

```
### K6
Adjust environment variables in Docker Compose file to select the load scneario that you want to run.

```
cd k6
export AWS_COMMUNITY_DAY_LB_DNS_NAME=$(pulumi -C ../pulumi stack output url)
docker-compose run k6 run /scripts/k6_ramping_vus_script.js
```
