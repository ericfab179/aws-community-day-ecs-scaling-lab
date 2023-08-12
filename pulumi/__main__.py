# Based on https://www.pulumi.com/docs/clouds/aws/guides/ecs/

import logging
import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx


from requests import get
from datetime import datetime, timedelta


logging.basicConfig(level=logging.INFO)

# Create ECS cluster
cluster_name="aws-community-day-cluster"
cluster = aws.ecs.Cluster("cluster",
    name=cluster_name)

# Get VPC info
default_vpc = aws.ec2.get_vpc(default=True)
default_vpc_subnets = aws.ec2.get_subnet_ids(vpc_id=default_vpc.id)

# Create SG for Load Balancer
local_public_ip = get('https://api.ipify.org').content.decode('utf8')
lb_sg = aws.ec2.SecurityGroup("lb-sg",
    description="LB SG",
    vpc_id=default_vpc.id,
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        description="Allow whitelisted inbound traffic",
        from_port=8000,
        to_port=8000,
        protocol="tcp",
        cidr_blocks=[f"{local_public_ip}/32"],
    )],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        from_port=0,
        to_port=0,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"],
        ipv6_cidr_blocks=["::/0"],
    )],
    tags={
        "Name": "allow-whitelisted-ips",
    })

# Create Load Balancer
lb = awsx.lb.ApplicationLoadBalancer(
    "lb",
    default_target_group_port=8000,
    default_security_group=awsx.awsx.DefaultSecurityGroupArgs(security_group_id=lb_sg.id))

# Create ECS security group
ecs_sg = aws.ec2.SecurityGroup("ecs-sg",
    description="ECS service SG",
    vpc_id=default_vpc.id,
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        description="LB SG by reference",
        from_port=8000,
        to_port=8000,
        protocol="tcp",
        security_groups=[lb_sg.id],
    )],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        from_port=0,
        to_port=0,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"],
        ipv6_cidr_blocks=["::/0"],
    )],
    tags={
        "Name": "ecs-sg",
    })

# Create ECR repository
repository = awsx.ecr.Repository("repository", name="aws-community-day-sample-api-pulumi")

# Build image and push it to ECR repository https://www.pulumi.com/docs/clouds/aws/guides/ecs/#building-and-publishing-docker-images-automatically
image = awsx.ecr.Image("image",
    repository_url=repository.url,
    path="../app")


# Create ECS service
service_name = "aws-community-day-sample-api"
service = awsx.ecs.FargateService("service",
    name=service_name,
    cluster=cluster.arn,
    network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
        assign_public_ip=True,
        subnets=default_vpc_subnets.ids,
        security_groups=[ecs_sg.id],
    ),
    desired_count=1,
    task_definition_args=awsx.ecs.FargateServiceTaskDefinitionArgs(
        container=awsx.ecs.TaskDefinitionContainerDefinitionArgs(
            image=image.image_uri,
            cpu=256,
            memory=512,
            essential=True,
            port_mappings=[awsx.ecs.TaskDefinitionPortMappingArgs(
                target_group=lb.default_target_group,
                container_port=8000,
                host_port=8000
            )],
        ),
    ))

# Set LB DNS as Pulumi output
pulumi.export("url", lb.load_balancer.dns_name)



### AUTOSCALING

# # Create App Autoscaling ECS target
ecs_target = aws.appautoscaling.Target("ecsTarget",
    max_capacity=5,
    min_capacity=1,
    resource_id=f"service/{cluster_name}/{service_name}",
    scalable_dimension="ecs:service:DesiredCount",
    service_namespace="ecs",
    opts=pulumi.ResourceOptions(depends_on=[service]))

# Target tracking configurations
target_tracking_config_alb_request_count = aws.appautoscaling.PolicyTargetTrackingScalingPolicyConfigurationArgs(
        target_value=50,
        predefined_metric_specification=aws.appautoscaling.PolicyTargetTrackingScalingPolicyConfigurationPredefinedMetricSpecificationArgs(
            predefined_metric_type="ALBRequestCountPerTarget",
            resource_label = pulumi.Output.all(lb_suffix=lb.load_balancer.arn_suffix, tg_suffix=lb.default_target_group.arn_suffix).apply(lambda v: str(v['lb_suffix']) + '/' + str(v['tg_suffix']))
        )
    )

target_tracking_config_cpu_avg = aws.appautoscaling.PolicyTargetTrackingScalingPolicyConfigurationArgs(
        target_value=60,
        predefined_metric_specification=aws.appautoscaling.PolicyTargetTrackingScalingPolicyConfigurationPredefinedMetricSpecificationArgs(
            predefined_metric_type="ECSServiceAverageCPUUtilization"
        )
    )

# Target tracking
target_tracking_ecs_policy = aws.appautoscaling.Policy("target_tracking_ecs_policy",
    policy_type="TargetTrackingScaling",
    resource_id=ecs_target.resource_id,
    scalable_dimension=ecs_target.scalable_dimension,
    service_namespace=ecs_target.service_namespace,
    target_tracking_scaling_policy_configuration=target_tracking_config_cpu_avg # CHange this to set your desired target tracking configuration
)

# Step Scaling
step_scaling_ecs_policy = aws.appautoscaling.Policy("step_scaling_ecs_policy",
    policy_type="StepScaling",
    resource_id=ecs_target.resource_id,
    scalable_dimension=ecs_target.scalable_dimension,
    service_namespace=ecs_target.service_namespace,
    step_scaling_policy_configuration=aws.appautoscaling.PolicyStepScalingPolicyConfigurationArgs(
        adjustment_type="ChangeInCapacity",
        cooldown=60,
        metric_aggregation_type="Maximum",
        step_adjustments=[
            aws.appautoscaling.PolicyStepScalingPolicyConfigurationStepAdjustmentArgs(
                metric_interval_lower_bound = "0",
                metric_interval_upper_bound = "300",
                scaling_adjustment=2,
            ),
            aws.appautoscaling.PolicyStepScalingPolicyConfigurationStepAdjustmentArgs(
                metric_interval_lower_bound = "300",
                scaling_adjustment=4,
            ),
        ],
    ))

# Step Scaling Alarm
step_scaling_metric_alarm = aws.cloudwatch.MetricAlarm("StepScalingMetricAlarm",
    comparison_operator="GreaterThanOrEqualToThreshold",
    evaluation_periods=1,
    metric_name="RequestCount",
    namespace="AWS/ApplicationELB",
    period=60,
    statistic="Sum",
    threshold=100,
    dimensions={
        "LoadBalancer": lb.load_balancer.arn_suffix.apply(lambda lb_suffix: str(lb_suffix)),
    },
    alarm_description="This metric monitors ALB request count.",
    alarm_actions=[step_scaling_ecs_policy.arn])


# Scheduled Scaling

base_datetime = datetime.now()
increase_capacity_datetime = base_datetime + timedelta(minutes=5)
decrease_capacity_datetime = base_datetime + timedelta(minutes=10)

ecs_scheduled_action_increase_capacity = aws.appautoscaling.ScheduledAction("ecsScheduledActionIncrease",
    service_namespace=ecs_target.service_namespace,
    resource_id=ecs_target.resource_id,
    scalable_dimension=ecs_target.scalable_dimension,
    schedule=f"at({increase_capacity_datetime.strftime('%Y-%m-%dT%H:%M:%S')})",
    timezone="America/Bogota",
    scalable_target_action=aws.appautoscaling.ScheduledActionScalableTargetActionArgs(
        min_capacity=4,
        max_capacity=6,
    ))

ecs_scheduled_action_reduce_capacity = aws.appautoscaling.ScheduledAction("ecsScheduledActionReduce",
    service_namespace=ecs_target.service_namespace,
    resource_id=ecs_target.resource_id,
    scalable_dimension=ecs_target.scalable_dimension,
    schedule=f"at({decrease_capacity_datetime.strftime('%Y-%m-%dT%H:%M:%S')})",
    timezone="America/Bogota",
    scalable_target_action=aws.appautoscaling.ScheduledActionScalableTargetActionArgs(
        min_capacity=1,
        max_capacity=5,
    ))
