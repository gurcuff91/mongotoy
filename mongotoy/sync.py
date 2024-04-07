import asyncio
import functools
from typing import Callable, AsyncGenerator, Generator

# Flag to indicate whether sync mode is enabled
_SYNC_MODE_ENABLED = False

# Global event loop
_loop = asyncio.get_event_loop()


def enable_sync_mode():
    """
    Enable synchronous mode for running asynchronous functions synchronously.
    """
    global _SYNC_MODE_ENABLED
    _SYNC_MODE_ENABLED = True


def run_sync(func: Callable):
    """
    Wrapper function to run an asynchronous function synchronously.

    Args:
        func (Callable): The asynchronous function to run.

    Returns:
        Callable: A wrapped function that runs the asynchronous function synchronously.
    """

    def wrap(*args, **kwargs):
        return _loop.run_until_complete(func(*args, **kwargs))

    return wrap


def as_sync_gen(gen: AsyncGenerator) -> Generator:
    """
    Convert an asynchronous generator into a synchronous generator.

    Args:
        gen (AsyncGenerator): The asynchronous generator.

    Yields:
        Any: Items yielded by the asynchronous generator.
    """
    while True:
        try:
            yield _loop.run_until_complete(gen.__anext__())
        except StopAsyncIteration:
            break


def proxy(func: Callable):
    """
    Decorator to run an asynchronous function synchronously if sync mode is enabled.

    Args:
        func (Callable): The asynchronous function to decorate.

    Returns:
        Callable: A wrapped function that runs the asynchronous function synchronously if sync mode is enabled.
    """

    @functools.wraps(func)
    def wrap(*args, **kwargs):
        if _SYNC_MODE_ENABLED:
            return run_sync(func)(*args, **kwargs)
        return func(*args, **kwargs)

    return wrap
