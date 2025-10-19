import asyncio
from collections.abc import Awaitable
from threading import Thread


def sync_await[T](future: Awaitable[T]) -> T:
    result = None

    def set_result():
        loop = asyncio.new_event_loop()

        try:
            asyncio.set_event_loop(loop)

            nonlocal result
            result = loop.run_until_complete(future)

        finally:
            loop.close()

    thread = Thread(target=set_result)

    thread.start()
    thread.join()

    return result
