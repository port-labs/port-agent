import logging

from core.config import settings
from streamers.streamer_factory import StreamerFactory

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


def main() -> None:
    streamer_factory = StreamerFactory()
    streamer = streamer_factory.get_streamer(settings.PORT_AGENT_TRANSPORT_TYPE)
    logger.info("Starting streaming with transport type: %s", settings.PORT_AGENT_TRANSPORT_TYPE)
    streamer.stream()


if __name__ == "__main__":
    main()
