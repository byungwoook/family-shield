"""Delete case text 30 days after the decision (milestone 7). Run it daily.

    python -m scripts.purge_case_text

Clears the transcript, the parent's text, and the claims of every case
decided at least 30 days ago. The result, the pattern id, the timeline, and
the member stay. Prints only a count, never any text.
"""

import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from backend.store import purge_case_text


def main() -> int:
    load_dotenv()
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        print("Set DATABASE_URL first.", file=sys.stderr)
        return 2
    import psycopg

    with psycopg.connect(url) as conn:
        changed = purge_case_text(conn, now=datetime.now(timezone.utc))
        conn.commit()
    print(f"{changed} case(s) cleared.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
