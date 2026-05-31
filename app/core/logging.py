import logging

from utils import sanitize_for_log


class SanitizeLogFilter(logging.Filter):
    """Redact secrets from log message templates and formatting args."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.msg is not None:
            record.msg = sanitize_for_log(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: sanitize_for_log(value) for key, value in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(sanitize_for_log(arg) for arg in record.args)
            else:
                record.args = sanitize_for_log(record.args)

        return True


def configure_sanitized_logging(level: str | int = logging.INFO) -> None:
    logging.basicConfig(level=level, force=True)

    filt = SanitizeLogFilter()
    for handler in logging.getLogger().handlers:
        if not any(
            isinstance(existing, SanitizeLogFilter) for existing in handler.filters
        ):
            handler.addFilter(filt)
