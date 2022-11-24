from streamers.base_streamer import BaseStreamer
from streamers.kafka.kafka_to_webhook_streamer import KafkaToWebhookStreamer


class StreamerFactory:
    @staticmethod
    def get_streamer(name: str) -> BaseStreamer:
        if name == "KafkaToWebhookStreamer":
            return KafkaToWebhookStreamer()

        raise Exception("Not found streamer for name: %s" % name)
