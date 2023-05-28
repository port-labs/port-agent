from streamers.base_streamer import BaseStreamer
from streamers.kafka.kafka_to_gitlab_streamer import KafkaToGitLabStreamer
from streamers.kafka.kafka_to_webhook_streamer import KafkaToWebhookStreamer


class StreamerFactory:
    @staticmethod
    def get_streamer(name: str) -> BaseStreamer:
        if name == "KafkaToWebhookStreamer":
            return KafkaToWebhookStreamer()
        if name == "KafkaToGitLabStreamer":
            return KafkaToGitLabStreamer()

        raise Exception("Not found streamer for name: %s" % name)
