import asyncio
import sys

if sys.platform == "win32":
    # Required: psycopg async needs SelectorEventLoop on Windows.
    # Deprecated in 3.14, removed in 3.16 — revisit when uvicorn supports loop_factory.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # type: ignore[deprecated]

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
