from core.consts import consts
from streamers.base_streamer import BaseStreamer
from streamers.kafka.kafka_streamer import KafkaStreamer
from streamers.polling.polling_streamer import PollingStreamer


class StreamerFactory:
    @staticmethod
    def get_streamer(streamer_type: str) -> BaseStreamer:
        if streamer_type not in consts.VALID_STREAMER_TYPES:
            raise ValueError(
                f"STREAMER_NAME must be one of {consts.VALID_STREAMER_TYPES}, "
                f"got: {streamer_type}"
            )

        return KafkaStreamer() if streamer_type == "KAFKA" else PollingStreamer()
