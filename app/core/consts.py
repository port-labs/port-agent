from streamers.kafka.kafka_to_gitlab_streamer import KafkaToGitLabStreamer
from streamers.kafka.kafka_to_webhook_streamer import KafkaToWebhookStreamer


class Consts:
    KAFKA_STREAMERS = {"WEBHOOK": KafkaToWebhookStreamer,
                       "GITLAB": KafkaToGitLabStreamer}
    KAFKA_CONSUMER_CLIENT_ID = "port-agent"


consts = Consts()
