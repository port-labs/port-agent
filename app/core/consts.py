from streamers.kafka.kafka_to_gitlab_processor import KafkaToGitLabProcessor
from streamers.kafka.kafka_to_webhook_processor import KafkaToWebhookProcessor


class Consts:
    KAFKA_STREAMERS = {"WEBHOOK": KafkaToWebhookProcessor,
                       "GITLAB": KafkaToGitLabProcessor}
    KAFKA_CONSUMER_CLIENT_ID = "port-agent"


consts = Consts()
