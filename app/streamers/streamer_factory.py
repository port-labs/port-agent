from core.config import settings
from streamers.base_streamer import BaseStreamer
from streamers.kafka.kafka_streamer import KafkaStreamer


class StreamerFactory:
    @staticmethod
    def get_streamer(name: str) -> BaseStreamer:
        if settings.STREAMER_NAME == "Kafka":
            return KafkaStreamer()

        raise Exception("Not found streamer for name: %s" % name)
