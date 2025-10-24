import json
import os.path
import re
import sqlite3
from typing import Any, Dict, List

import structlog

from .search import Searcher

log = structlog.stdlib.get_logger("chat")


class SqliteSearch(Searcher):

    def __init__(self, *_args, **_kwargs):
        self.db_path = os.path.join("tmp", "docs.db")

    async def search(
        self,
        query: str,
        gl_version: str,
        page_size: int = 20,
        **kwargs: Any,
    ) -> List[Dict[Any, Any]]:
        if os.path.isfile(self.db_path):
            conn = sqlite3.connect(self.db_path)
            indexer = conn.cursor()
        else:
            conn = None
            indexer = None

        if not indexer:
            log.warning("SqliteSearch: No database found for documentation searches.")

            return []

        # We need to remove punctuation because table was created with FTS5
        # see https://stackoverflow.com/questions/46525854/sqlite3-fts5-error-when-using-punctuation
        sanitized_query = re.sub(r"[^\w\s]", "", query, flags=re.UNICODE)

        data = indexer.execute(
            "SELECT metadata, content FROM doc_index WHERE processed MATCH ? ORDER BY bm25(doc_index) LIMIT ?",
            (sanitized_query, page_size),
        )

        results = self._parse_response(data)

        if conn:
            conn.close()

        return results

    def provider(self):
        return "sqlite"

    def _parse_response(self, response):
        results = []

        for r in response:
            metadata = json.loads(r[0])
            search_result = {
                "id": metadata["filename"],
                "content": r[1],
                "metadata": metadata,
            }
            results.append(search_result)
        return results
