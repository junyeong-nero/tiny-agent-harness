def truncate(value: str, limit: int = 240) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."
