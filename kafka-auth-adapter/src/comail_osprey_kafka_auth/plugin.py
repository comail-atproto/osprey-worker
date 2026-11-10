import os
import platform
from collections.abc import Mapping, Sequence
from pathlib import Path
from kafka import KafkaProducer
from kafka.coordinator.assignors.roundrobin import RoundRobinPartitionAssignor
from osprey.engine.executor.execution_context import Action
from osprey.worker.adaptor.plugin_manager import hookimpl_osprey
from osprey.worker.lib.config import Config
from osprey.worker.sinks.sink.input_stream import BaseInputStream, KafkaInputStream
from osprey.worker.sinks.sink.kafka_output_sink import KafkaOutputSink
from osprey.worker.sinks.sink.output_sink import BaseOutputSink
from osprey.worker.sinks.utils.acking_contexts import BaseAckingContext
from osprey.worker.sinks.utils.kafka import PatchedKafkaConsumer


def kafka_auth_options(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Read the optional SASL credentials without logging their values."""
    values = os.environ if environ is None else environ
    username = values.get("COMAIL_KAFKA_USERNAME")
    password_file = values.get("COMAIL_KAFKA_PASSWORD_FILE")

    if username is None and password_file is None:
        return {}
    if not username or not password_file:
        raise RuntimeError("COMAIL_KAFKA_USERNAME and COMAIL_KAFKA_PASSWORD_FILE must both be set")
    if "\n" in username or "\r" in username or "\0" in username:
        raise RuntimeError("COMAIL_KAFKA_USERNAME must be a single line")

    try:
        password = Path(password_file).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise RuntimeError("Kafka password file could not be read") from None
    if password.endswith("\r\n"):
        password = password[:-2]
    elif password.endswith("\n"):
        password = password[:-1]
    if not password or "\n" in password or "\r" in password or "\0" in password:
        raise RuntimeError("Kafka password file must contain one non-empty line")

    return {
        "security_protocol": "SASL_PLAINTEXT",
        "sasl_mechanism": "PLAIN",
        "sasl_plain_username": username,
        "sasl_plain_password": password,
    }


@hookimpl_osprey(tryfirst=True)
def register_input_stream(config: Config) -> BaseInputStream[BaseAckingContext[Action]] | None:
    """Create Osprey's Kafka input stream with the same subscription settings."""
    auth_options = kafka_auth_options()
    if not auth_options:
        return None

    client_id = config.get_str("OSPREY_KAFKA_INPUT_STREAM_CLIENT_ID", platform.node())
    client_id_suffix = config.get_optional_str("OSPREY_KAFKA_INPUT_STREAM_CLIENT_ID_SUFFIX")
    input_topic = config.get_str("OSPREY_KAFKA_INPUT_STREAM_TOPIC", "osprey.actions_input")
    bootstrap_servers = config.get_str_list("OSPREY_KAFKA_BOOTSTRAP_SERVERS", ["localhost"])
    group_id = config.get_optional_str("OSPREY_KAFKA_GROUP_ID")
    if client_id_suffix:
        client_id = f"{client_id}-{client_id_suffix}"

    consumer = PatchedKafkaConsumer(
        input_topic,
        bootstrap_servers=bootstrap_servers,
        client_id=client_id,
        group_id=group_id,
        partition_assignment_strategy=(RoundRobinPartitionAssignor,),
        **auth_options,
    )
    return KafkaInputStream(kafka_consumer=consumer)


@hookimpl_osprey
def register_output_sinks(config: Config) -> Sequence[BaseOutputSink]:
    """Create the upstream Kafka output sink when Comail enables it."""
    auth_options = kafka_auth_options()
    comail_output_enabled = config.get_bool("COMAIL_KAFKA_OUTPUT_SINK", False)
    osprey_output_enabled = config.get_bool("OSPREY_KAFKA_OUTPUT_SINK", False)
    if osprey_output_enabled and (comail_output_enabled or auth_options):
        raise RuntimeError(
            "Set OSPREY_KAFKA_OUTPUT_SINK=false when Kafka authentication is enabled"
        )
    if not comail_output_enabled:
        return []
    if not auth_options:
        raise RuntimeError("COMAIL_KAFKA_OUTPUT_SINK requires Kafka authentication credentials")

    output_topic = config.expect_str("OSPREY_KAFKA_OUTPUT_TOPIC")
    bootstrap_servers = config.expect_str_list("OSPREY_KAFKA_BOOTSTRAP_SERVERS")
    client_id = config.expect_str("OSPREY_KAFKA_OUTPUT_CLIENT_ID")
    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        client_id=client_id,
        **auth_options,
    )
    return [KafkaOutputSink(kafka_topic=output_topic, kafka_producer=producer)]
