from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pulumi
import pulumi_aws as aws


config = pulumi.Config()
aws_config = pulumi.Config("aws")

stack_env = config.require("env")
aws_profile = config.require("awsProfile")
expected_aws_account_id = config.require("expectedAwsAccountId")
lambda_configs: dict[str, dict[str, Any]] = config.require_object("lambda")

PLACEHOLDER_VALUES = {
    "secret_xxx",
    "your_notion_database_id",
    "your_notion_data_source_id",
    "your_youtube_playlist_id",
}


def validate_config_value(name: str, value: str) -> str:
    if value in PLACEHOLDER_VALUES or value.startswith("your_"):
        raise ValueError(f"Pulumi config {name} still contains a placeholder value.")
    return value


youtube_playlist_id = validate_config_value(
    "youtubePlaylistId",
    config.require("youtubePlaylistId"),
)
notion_token = config.require_secret("notionToken").apply(
    lambda value: validate_config_value("notionToken", value)
)
notion_database_id = validate_config_value(
    "notionDatabaseId",
    config.require("notionDatabaseId"),
)
notion_data_source_id = config.get("notionDataSourceId") or ""
if notion_data_source_id:
    notion_data_source_id = validate_config_value(
        "notionDataSourceId",
        notion_data_source_id,
    )
notion_use_default_template = config.get_bool("notionUseDefaultTemplate") or False
youtube_enrich_lengths = config.get_bool("youtubeEnrichLengths")
if youtube_enrich_lengths is None:
    youtube_enrich_lengths = True

repo_root = Path(__file__).resolve().parent.parent
bundle_dir = repo_root / ".pulumi" / "lambda"
if not bundle_dir.is_dir():
    raise RuntimeError(
        "Lambda bundle is missing. Run ./script/build-lambda.sh before pulumi up."
    )

personal_aws = aws.Provider(
    "personal-sandbox",
    region=aws_config.require("region"),
    profile=aws_profile,
    allowed_account_ids=[expected_aws_account_id],
)


def resource_options(
    *,
    depends_on: list[pulumi.Resource] | None = None,
) -> pulumi.ResourceOptions:
    return pulumi.ResourceOptions(
        provider=personal_aws,
        depends_on=depends_on,
    )


def create_lambda_execution_role(resource_base_name: str) -> tuple[
    aws.iam.Role,
    aws.iam.RolePolicyAttachment,
]:
    role = aws.iam.Role(
        f"{resource_base_name}-exec-role",
        name=f"{resource_base_name}-exec-role",
        assume_role_policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ),
        opts=resource_options(),
    )

    policy_attachment = aws.iam.RolePolicyAttachment(
        f"{resource_base_name}-log-policy-attach",
        role=role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        opts=resource_options(),
    )

    return role, policy_attachment


lambda_exports: dict[str, dict[str, pulumi.Output[str]]] = {}

for function_key, function_config in lambda_configs.items():
    resource_base_name = f"{stack_env}-fn-{function_key}"
    role, policy_attachment = create_lambda_execution_role(resource_base_name)

    log_group = aws.cloudwatch.LogGroup(
        f"{resource_base_name}-log-group",
        name=f"/aws/lambda/{resource_base_name}",
        retention_in_days=function_config["logRetentionDays"],
        opts=resource_options(),
    )

    function = aws.lambda_.Function(
        resource_base_name,
        name=resource_base_name,
        description=function_config["description"],
        runtime=function_config["runtime"],
        handler=function_config["handler"],
        role=role.arn,
        code=pulumi.AssetArchive({".": pulumi.FileArchive(str(bundle_dir))}),
        timeout=function_config["timeout"],
        memory_size=function_config["memoryMb"],
        reserved_concurrent_executions=function_config.get("reservedConcurrency"),
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables={
                "YOUTUBE_PLAYLIST_ID": youtube_playlist_id,
                "NOTION_TOKEN": notion_token,
                "NOTION_DATABASE_ID": notion_database_id,
                "NOTION_DATA_SOURCE_ID": notion_data_source_id,
                "NOTION_USE_DEFAULT_TEMPLATE": str(
                    notion_use_default_template
                ).lower(),
                "YOUTUBE_ENRICH_LENGTHS": str(youtube_enrich_lengths).lower(),
            }
        ),
        opts=resource_options(depends_on=[log_group, policy_attachment]),
    )

    schedule = aws.cloudwatch.EventRule(
        f"{resource_base_name}-daily-schedule",
        name=f"{resource_base_name}-daily-schedule",
        description="Run the YouTube to Notion sync once per day at 00:00 UTC.",
        schedule_expression="cron(0 0 * * ? *)",
        state="ENABLED",
        opts=resource_options(),
    )

    invoke_permission = aws.lambda_.Permission(
        f"{resource_base_name}-schedule-invoke-permission",
        action="lambda:InvokeFunction",
        function=function.name,
        principal="events.amazonaws.com",
        source_arn=schedule.arn,
        opts=resource_options(),
    )

    aws.cloudwatch.EventTarget(
        f"{resource_base_name}-daily-schedule-target",
        rule=schedule.name,
        arn=function.arn,
        input=json.dumps({}),
        opts=resource_options(depends_on=[invoke_permission]),
    )

    lambda_exports[function_key] = {
        "name": function.name,
        "arn": function.arn,
        "scheduleName": schedule.name,
    }

for function_key, details in lambda_exports.items():
    pulumi.export(f"{function_key}_name", details["name"])
    pulumi.export(f"{function_key}_arn", details["arn"])
    pulumi.export(f"{function_key}_schedule_name", details["scheduleName"])
