"""Fast-path adapters. Each adapter exposes ``async read() -> dict``; failures propagate
to the channel layer, which converts them into explicit unavailable states."""
