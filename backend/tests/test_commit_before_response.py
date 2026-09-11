"""The database commit must land before the response does.

FastAPI runs a yield-dependency's exit code after the response is sent unless
the dependency is declared with scope="function". With the default, a client
that reads immediately after a 200 can see the state from before the write —
which showed up as "I have to reload the page to see what I just added".
This pins the scope, and proves the ordering through the ASGI interface.
"""

import asyncio
import unittest
from typing import get_args

from fastapi import FastAPI
from starlette.types import Message, Receive, Scope, Send

from app.db.session import get_session
from app.modules.household import providers as household
from app.modules.shopping import providers as shopping


class TestSessionScope(unittest.TestCase):
    def test_both_session_dependencies_close_before_the_response(self):
        for dep in (shopping.SessionDep, household.SessionDep):
            depends = get_args(dep)[1]
            self.assertIs(depends.dependency, get_session)
            self.assertEqual(depends.scope, "function")


class TestOrderingThroughAsgi(unittest.TestCase):
    def test_the_dependency_exit_runs_before_the_body_is_sent(self):
        # A stand-in for the session: records when its exit code ran relative
        # to the response body being handed to the server.
        events: list[str] = []

        def unit_of_work():
            yield
            events.append("committed")

        app = FastAPI()
        from fastapi import Depends

        @app.get("/write")
        def write(_: None = Depends(unit_of_work, scope="function")) -> dict[str, str]:
            return {"ok": "yes"}

        async def run() -> None:
            scope: Scope = {
                "type": "http",
                "method": "GET",
                "path": "/write",
                "headers": [],
                "query_string": b"",
                "scheme": "http",
                "server": ("test", 80),
                "client": ("t", 1),
            }

            async def receive() -> Message:
                await asyncio.sleep(0)  # yield to the loop, as a real server would
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message: Message) -> None:
                await asyncio.sleep(0)
                if message["type"] == "http.response.body":
                    events.append("body sent")

            receive_fn: Receive = receive
            send_fn: Send = send
            await app(scope, receive_fn, send_fn)

        asyncio.run(run())

        self.assertEqual(events, ["committed", "body sent"])


if __name__ == "__main__":
    unittest.main()
