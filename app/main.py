import logging

from core.config import settings
from streamers.streamer_factory import StreamerFactory

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


def main() -> None:
    streamer_factory = StreamerFactory()
    streamer = streamer_factory.get_streamer(settings.STREAMER_NAME)
    logger.info("Starting streaming with streamer: %s", settings.STREAMER_NAME)
    streamer.stream()


if __name__ == "__main__":
    main()
