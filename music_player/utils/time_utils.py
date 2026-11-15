"""Timestamp formatting helpers."""


def ms_to_display(ms: int) -> str:
    """Convert milliseconds to M:SS or H:MM:SS display string."""
    if ms < 0:
        ms = 0
    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def ms_to_timestamp(ms: int) -> str:
    """Convert milliseconds to HH:MM:SS.mmm timestamp string."""
    if ms < 0:
        ms = 0
    total_seconds = ms // 1000
    remainder_ms = ms % 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{remainder_ms:03d}"


def timestamp_to_ms(timestamp: str) -> int:
    """Convert HH:MM:SS.mmm or MM:SS.mmm timestamp string to milliseconds."""
    parts = timestamp.split(":")
    if len(parts) == 3:
        hours, minutes, sec_ms = parts
    elif len(parts) == 2:
        hours = "0"
        minutes, sec_ms = parts
    else:
        raise ValueError(f"Invalid timestamp format: {timestamp}")

    if "." in sec_ms:
        seconds, ms_str = sec_ms.split(".")
        # Pad or truncate to 3 digits
        ms_str = ms_str[:3].ljust(3, "0")
    else:
        seconds = sec_ms
        ms_str = "0"

    return (
        int(hours) * 3600000
        + int(minutes) * 60000
        + int(seconds) * 1000
        + int(ms_str)
    )
