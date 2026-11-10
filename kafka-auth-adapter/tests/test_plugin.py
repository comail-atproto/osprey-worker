from importlib.metadata import entry_points
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from comail_osprey_kafka_auth import plugin
from comail_osprey_kafka_auth.plugin import kafka_auth_options
from osprey.worker.adaptor.plugin_manager import bootstrap_input_stream, load_all_osprey_plugins


class FakeConfig:
    def __init__(self, **values):
        self.values = values

    def get_str(self, name, default=None):
        return self.values.get(name, default)

    def get_optional_str(self, name):
        return self.values.get(name)

    def get_str_list(self, name, default=None):
        return self.values.get(name, default)

    def get_bool(self, name, default=False):
        return self.values.get(name, default)

    def expect_str(self, name):
        return self.values[name]

    def expect_str_list(self, name):
        return self.values[name]


def create_password_file(test_case, content: str) -> Path:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as file:
        file.write(content)
    path = Path(file.name)
    test_case.addCleanup(path.unlink, missing_ok=True)
    return path


class KafkaAuthOptionsTests(unittest.TestCase):
    def test_missing_credentials_leave_the_client_unauthenticated(self):
        self.assertEqual({}, kafka_auth_options({}))

    def test_credentials_enable_sasl_plain_without_changing_password_text(self):
        password_file = create_password_file(self, "synthetic-password \n")
        environment = {
            "COMAIL_KAFKA_USERNAME": "synthetic-user",
            "COMAIL_KAFKA_PASSWORD_FILE": str(password_file),
        }
        self.assertEqual(
            {
                "security_protocol": "SASL_PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": "synthetic-user",
                "sasl_plain_password": "synthetic-password ",
            },
            kafka_auth_options(environment),
        )

    def test_credentials_reject_nul_and_extra_line_endings(self):
        for password in ("nul\0value", "extra\n\n", "extra\r\n\n"):
            with self.subTest(password=password):
                password_file = create_password_file(self, password)
                with self.assertRaisesRegex(RuntimeError, "password file"):
                    kafka_auth_options(
                        {
                            "COMAIL_KAFKA_USERNAME": "synthetic-user",
                            "COMAIL_KAFKA_PASSWORD_FILE": str(password_file),
                        }
                    )
        with self.assertRaisesRegex(RuntimeError, "single line"):
            kafka_auth_options(
                {
                    "COMAIL_KAFKA_USERNAME": "synthetic\0user",
                    "COMAIL_KAFKA_PASSWORD_FILE": "/unused",
                }
            )

    def test_partial_credentials_fail_without_echoing_values(self):
        for environment in (
            {"COMAIL_KAFKA_USERNAME": "synthetic-user"},
            {"COMAIL_KAFKA_PASSWORD_FILE": "/synthetic/password"},
        ):
            with self.subTest(environment=environment):
                with self.assertRaisesRegex(RuntimeError, "both") as raised:
                    kafka_auth_options(environment)
                self.assertNotIn("synthetic-user", str(raised.exception))
                self.assertNotIn("/synthetic/password", str(raised.exception))

    def test_empty_or_unreadable_password_files_fail_without_echoing_values(self):
        password_file = create_password_file(self, "")
        for path in (password_file, "/synthetic/missing-password"):
            with self.subTest(path=path):
                environment = {
                    "COMAIL_KAFKA_USERNAME": "synthetic-user",
                    "COMAIL_KAFKA_PASSWORD_FILE": str(path),
                }
                with self.assertRaisesRegex(RuntimeError, "password file") as raised:
                    kafka_auth_options(environment)
                self.assertNotIn("synthetic-user", str(raised.exception))
                self.assertNotIn(str(path), str(raised.exception))

    def test_multiline_password_files_fail(self):
        password_file = create_password_file(self, "first-line\nsecond-line\n")
        with self.assertRaisesRegex(RuntimeError, "password file"):
            kafka_auth_options(
                {
                    "COMAIL_KAFKA_USERNAME": "synthetic-user",
                    "COMAIL_KAFKA_PASSWORD_FILE": str(password_file),
                }
            )


class KafkaPluginTests(unittest.TestCase):
    def test_adapter_is_installed_as_an_osprey_plugin(self):
        plugin_names = {entry_point.name for entry_point in entry_points(group="osprey_plugin")}
        self.assertIn("comail_kafka_auth", plugin_names)

    def test_input_plugin_leaves_existing_plugins_in_control_without_credentials(self):
        config = FakeConfig(
            OSPREY_KAFKA_INPUT_STREAM_CLIENT_ID="synthetic-worker",
            OSPREY_KAFKA_INPUT_STREAM_CLIENT_ID_SUFFIX="one",
            OSPREY_KAFKA_INPUT_STREAM_TOPIC="osprey.actions_input",
            OSPREY_KAFKA_BOOTSTRAP_SERVERS=["kafka:9092"],
            OSPREY_KAFKA_GROUP_ID="osprey-comail",
        )
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(plugin, "PatchedKafkaConsumer") as consumer_factory,
            patch.object(plugin, "KafkaInputStream") as stream_factory,
        ):
            self.assertIsNone(plugin.register_input_stream(config))
        consumer_factory.assert_not_called()
        stream_factory.assert_not_called()

    def test_input_plugin_passes_authentication_options_from_the_runtime_file(self):
        password_file = create_password_file(self, "synthetic-password\n")
        config = FakeConfig(OSPREY_KAFKA_BOOTSTRAP_SERVERS=["kafka:9092"])
        with (
            patch.dict(
                "os.environ",
                {
                    "COMAIL_KAFKA_USERNAME": "worker",
                    "COMAIL_KAFKA_PASSWORD_FILE": str(password_file),
                },
                clear=True,
            ),
            patch.object(plugin, "PatchedKafkaConsumer") as consumer_factory,
            patch.object(plugin, "KafkaInputStream", return_value=object()),
        ):
            plugin.register_input_stream(config)
        self.assertEqual("SASL_PLAINTEXT", consumer_factory.call_args.kwargs["security_protocol"])
        self.assertEqual("PLAIN", consumer_factory.call_args.kwargs["sasl_mechanism"])
        self.assertEqual("worker", consumer_factory.call_args.kwargs["sasl_plain_username"])
        self.assertEqual("synthetic-password", consumer_factory.call_args.kwargs["sasl_plain_password"])

    def test_installed_plugin_manager_selects_comail_input_over_upstream_example(self):
        from atproto_plugin import register_plugins as atproto_plugin

        config = FakeConfig(
            OSPREY_KAFKA_INPUT_STREAM_CLIENT_ID="synthetic-worker",
            OSPREY_KAFKA_INPUT_STREAM_TOPIC="synthetic.input",
            OSPREY_KAFKA_BOOTSTRAP_SERVERS=["kafka:9092"],
            OSPREY_KAFKA_GROUP_ID="synthetic-group",
        )
        password_file = create_password_file(self, "synthetic-password\n")
        stream = object()
        load_all_osprey_plugins()
        with (
            patch.dict(
                "os.environ",
                {
                    "COMAIL_KAFKA_USERNAME": "worker",
                    "COMAIL_KAFKA_PASSWORD_FILE": str(password_file),
                },
                clear=True,
            ),
            patch.object(plugin, "PatchedKafkaConsumer") as consumer_factory,
            patch.object(plugin, "KafkaInputStream", return_value=stream),
            patch.object(atproto_plugin, "JetStreamInputStream") as jetstream_factory,
        ):
            selected_stream = bootstrap_input_stream(config)
        self.assertIs(stream, selected_stream)
        self.assertEqual(
            {
                "bootstrap_servers": ["kafka:9092"],
                "client_id": "synthetic-worker",
                "group_id": "synthetic-group",
                "partition_assignment_strategy": (plugin.RoundRobinPartitionAssignor,),
                "security_protocol": "SASL_PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": "worker",
                "sasl_plain_password": "synthetic-password",
            },
            consumer_factory.call_args.kwargs,
        )
        jetstream_factory.assert_not_called()

    def test_installed_plugin_manager_keeps_upstream_input_when_auth_is_absent(self):
        from atproto_plugin import register_plugins as atproto_plugin

        config = FakeConfig()
        stream = object()
        load_all_osprey_plugins()
        with (
            patch.dict("os.environ", {}, clear=True),
            patch.object(plugin, "PatchedKafkaConsumer") as consumer_factory,
            patch.object(atproto_plugin, "JetStreamInputStream", return_value=stream) as jetstream_factory,
        ):
            selected_stream = bootstrap_input_stream(config)
        self.assertIs(stream, selected_stream)
        jetstream_factory.assert_called_once_with(endpoint=None, wanted_collections=None)
        consumer_factory.assert_not_called()

    def test_output_plugin_reuses_osprey_sink_and_rejects_duplicate_plaintext_sink(self):
        config = FakeConfig(
            COMAIL_KAFKA_OUTPUT_SINK=True,
            OSPREY_KAFKA_OUTPUT_SINK=True,
            OSPREY_KAFKA_OUTPUT_TOPIC="osprey.execution_results",
            OSPREY_KAFKA_BOOTSTRAP_SERVERS=["kafka:9092"],
            OSPREY_KAFKA_OUTPUT_CLIENT_ID="synthetic-worker-output",
        )
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OSPREY_KAFKA_OUTPUT_SINK"):
                plugin.register_output_sinks(config)

    def test_comail_output_sink_fails_when_authentication_is_absent(self):
        config = FakeConfig(COMAIL_KAFKA_OUTPUT_SINK=True, OSPREY_KAFKA_OUTPUT_SINK=False)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "requires Kafka authentication"):
                plugin.register_output_sinks(config)

    def test_auth_credentials_cannot_fall_back_to_stock_output(self):
        password_file = create_password_file(self, "synthetic-password\n")
        config = FakeConfig(OSPREY_KAFKA_OUTPUT_SINK=True)
        with (
            patch.dict(
                "os.environ",
                {
                    "COMAIL_KAFKA_USERNAME": "worker",
                    "COMAIL_KAFKA_PASSWORD_FILE": str(password_file),
                },
                clear=True,
            ),
            self.assertRaisesRegex(RuntimeError, "OSPREY_KAFKA_OUTPUT_SINK"),
        ):
            plugin.register_output_sinks(config)

    def test_output_plugin_leaves_upstream_sink_alone_when_not_enabled(self):
        config = FakeConfig(OSPREY_KAFKA_OUTPUT_SINK=True)
        with patch.dict("os.environ", {}, clear=True), patch.object(plugin, "KafkaProducer") as producer_factory:
            self.assertEqual([], plugin.register_output_sinks(config))
        producer_factory.assert_not_called()

    def test_output_plugin_wraps_sasl_producer_in_the_upstream_sink(self):
        password_file = create_password_file(self, "synthetic-password\n")
        config = FakeConfig(
            COMAIL_KAFKA_OUTPUT_SINK=True,
            OSPREY_KAFKA_OUTPUT_SINK=False,
            OSPREY_KAFKA_OUTPUT_TOPIC="osprey.execution_results",
            OSPREY_KAFKA_BOOTSTRAP_SERVERS=["kafka:9092"],
            OSPREY_KAFKA_OUTPUT_CLIENT_ID="synthetic-worker-output",
        )
        producer = object()
        sink = object()
        with (
            patch.dict(
                "os.environ",
                {
                    "COMAIL_KAFKA_USERNAME": "worker",
                    "COMAIL_KAFKA_PASSWORD_FILE": str(password_file),
                },
                clear=True,
            ),
            patch.object(plugin, "KafkaProducer", return_value=producer) as producer_factory,
            patch.object(plugin, "KafkaOutputSink", return_value=sink) as sink_factory,
        ):
            self.assertEqual([sink], plugin.register_output_sinks(config))
        producer_factory.assert_called_once_with(
            bootstrap_servers=["kafka:9092"],
            client_id="synthetic-worker-output",
            security_protocol="SASL_PLAINTEXT",
            sasl_mechanism="PLAIN",
            sasl_plain_username="worker",
            sasl_plain_password="synthetic-password",
        )
        sink_factory.assert_called_once_with(
            kafka_topic="osprey.execution_results", kafka_producer=producer
        )


if __name__ == "__main__":
    unittest.main()
