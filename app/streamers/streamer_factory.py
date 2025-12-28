from streamers.base_streamer import BaseStreamer
from streamers.kafka.kafka_streamer import KafkaStreamer
from streamers.polling.polling_streamer import PollingStreamer


class StreamerFactory:
    @staticmethod
    def get_streamer(streamer_type: str) -> BaseStreamer:
        valid_types = ["KAFKA", "POLLING"]
        if streamer_type not in valid_types:
            raise ValueError(
                f"PORT_AGENT_STREAMER_TYPE must be one of {valid_types}, "
                f"got: {streamer_type}"
            )

        return KafkaStreamer() if streamer_type == "KAFKA" else PollingStreamer()
