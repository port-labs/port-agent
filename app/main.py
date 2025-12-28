import logging

from core.config import settings
from port_client import patch_org_streamer_setting
from streamers.streamer_factory import StreamerFactory

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


def main() -> None:
    try:
        logger.info(
            "Updating org streamer setting to match streamer type: %s",
            settings.STREAMER_NAME,
        )
        patch_org_streamer_setting(settings.STREAMER_NAME)
    except Exception as error:
        logger.warning(
            "Failed to update org streamer setting: %s. Continuing startup...",
            str(error),
        )

    streamer_factory = StreamerFactory()
    streamer = streamer_factory.get_streamer(settings.STREAMER_NAME)
    logger.info(
        "Starting streaming with streamer type: %s", settings.STREAMER_NAME
    )
    streamer.stream()


if __name__ == "__main__":
    main()
