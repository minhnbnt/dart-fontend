import asyncio
from collections.abc import Awaitable
from threading import Thread


def sync_await[T](future: Awaitable[T]) -> T:
    result = None
    exception = None

    def set_result():
        loop = asyncio.new_event_loop()

        try:
            asyncio.set_event_loop(loop)

            nonlocal result, exception
            result = loop.run_until_complete(future)

        except Exception as e:
            exception = e

        finally:
            loop.close()

    thread = Thread(target=set_result)

    thread.start()
    thread.join()

    if exception is not None:
        raise exception

    return result
