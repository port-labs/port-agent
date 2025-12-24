from streamers.base_streamer import BaseStreamer
from streamers.https.https_streamer import HttpsStreamer
from streamers.kafka.kafka_streamer import KafkaStreamer


class StreamerFactory:
    @staticmethod
    def get_streamer(transport_type: str) -> BaseStreamer:
        valid_types = ["KAFKA", "HTTPS"]
        if transport_type not in valid_types:
            raise ValueError(
                f"PORT_AGENT_TRANSPORT_TYPE must be one of {valid_types}, "
                f"got: {transport_type}"
            )

        return KafkaStreamer() if transport_type == "KAFKA" else HttpsStreamer()
