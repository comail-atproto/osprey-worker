# Kafka authentication

Use SASL/PLAIN over an encrypted network to protect credentials in transit.

## Input

Set `OSPREY_INPUT_STREAM_SOURCE=plugin` and provide both
`COMAIL_KAFKA_USERNAME` and `COMAIL_KAFKA_PASSWORD_FILE`.

Mount the password file in the worker container. It must contain one non-empty
UTF-8 line. The worker reads it at startup and strips one trailing LF or CRLF.
Incomplete or invalid credentials stop startup. If both variables are absent,
Osprey's built-in input handles the stream.

## Output

Provide the same two credential variables. Set `COMAIL_KAFKA_OUTPUT_SINK=true`
and `OSPREY_KAFKA_OUTPUT_SINK=false` to run a single authenticated producer.

The adapter uses the existing Osprey topic, broker, and client ID settings.
If `COMAIL_KAFKA_OUTPUT_SINK` is unset, Osprey controls the output sinks.
