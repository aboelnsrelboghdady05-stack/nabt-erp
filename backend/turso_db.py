import os
import httpx
import base64
import time
from typing import Any, List, Dict, Optional, Tuple, Union

class TursoRow:
    def __init__(self, cols: List[str], values: List[Any]):
        self._cols = cols
        self._values = values
        self._mapping = {c: v for c, v in zip(cols, values)}

    def __getitem__(self, item: Union[int, str]) -> Any:
        if isinstance(item, int):
            return self._values[item]
        if item in self._mapping:
            return self._mapping[item]
        # Case insensitive match fallback
        lower_item = item.lower()
        for k, v in self._mapping.items():
            if k.lower() == lower_item:
                return v
        raise KeyError(f"Column '{item}' not found in row. Available columns: {self._cols}")

    def __contains__(self, key: str) -> bool:
        return key in self._mapping or key.lower() in [c.lower() for c in self._cols]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self) -> List[str]:
        return list(self._cols)

    def values(self) -> List[Any]:
        return list(self._values)

    def items(self) -> List[Tuple[str, Any]]:
        return list(self._mapping.items())

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __repr__(self) -> str:
        return f"TursoRow({self._mapping})"


def _to_turso_arg(val: Any) -> dict:
    if val is None:
        return {"type": "null"}
    elif isinstance(val, bool):
        return {"type": "integer", "value": "1" if val else "0"}
    elif isinstance(val, int):
        return {"type": "integer", "value": str(val)}
    elif isinstance(val, float):
        return {"type": "float", "value": val}
    elif isinstance(val, bytes):
        return {"type": "blob", "base64": base64.b64encode(val).decode("ascii")}
    else:
        return {"type": "text", "value": str(val)}


def _from_turso_value(cell: dict) -> Any:
    if not isinstance(cell, dict):
        return cell
    t = cell.get("type")
    v = cell.get("value")
    if t == "null":
        return None
    elif t == "integer":
        return int(v) if v is not None else None
    elif t == "float":
        return float(v) if v is not None else None
    elif t == "text":
        return v
    elif t == "blob":
        b64 = cell.get("base64", "")
        return base64.b64decode(b64)
    return v


# ==============================================================================
# Global Shared Client Pool & Micro-Cache for Sub-Millisecond Speed
# ==============================================================================
_SHARED_CLIENT: Optional[httpx.Client] = None
_QUERY_CACHE: Dict[str, Tuple[float, List[str], List[List[Any]], Optional[int], int]] = {}
CACHE_TTL = 2.5  # 2.5 seconds cache for read-only queries during burst requests

def _get_shared_client(auth_token: str) -> httpx.Client:
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None or _SHARED_CLIENT.is_closed:
        _SHARED_CLIENT = httpx.Client(
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json"
            },
            timeout=httpx.Timeout(20.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=30, max_connections=60, keepalive_expiry=120.0)
        )
    return _SHARED_CLIENT

def clear_query_cache():
    global _QUERY_CACHE
    _QUERY_CACHE.clear()


class TursoCursor:
    def __init__(self, conn: "TursoConnection"):
        self.conn = conn
        self._rows: List[TursoRow] = []
        self._row_idx = 0
        self.lastrowid: Optional[int] = None
        self.rowcount: int = 0
        self.description: Optional[List[Tuple]] = None

    def execute(self, sql: str, params: Optional[Union[List, Tuple, dict]] = None) -> "TursoCursor":
        sql_stripped = sql.strip().rstrip(";")
        upper_sql = sql_stripped.upper()

        # Handle SQLite PRAGMA statements gracefully
        if upper_sql.startswith("PRAGMA"):
            if "table_info" in sql_stripped.lower():
                pass # let it run
            else:
                self._rows = []
                self.description = []
                self.lastrowid = None
                self.rowcount = 0
                return self

        # Mutation check: Clear cache if this is a write query
        is_read_query = upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")
        if not is_read_query:
            clear_query_cache()

        # Check in-memory query cache for read queries
        cache_key = None
        if is_read_query:
            try:
                cache_key = f"{sql_stripped}:{str(params)}"
                if cache_key in _QUERY_CACHE:
                    cached_time, cols, raw_rows, last_id, affected = _QUERY_CACHE[cache_key]
                    if time.time() - cached_time < CACHE_TTL:
                        self.description = [(c, None, None, None, None, None, None) for c in cols]
                        self._rows = [TursoRow(cols, list(r)) for r in raw_rows]
                        self._row_idx = 0
                        self.lastrowid = last_id
                        self.rowcount = affected
                        return self
            except Exception:
                cache_key = None

        stmt: Dict[str, Any] = {"sql": sql_stripped}
        if params is not None:
            if isinstance(params, (list, tuple)):
                stmt["args"] = [_to_turso_arg(p) for p in params]
            elif isinstance(params, dict):
                stmt["named_args"] = [{"name": k, "value": _to_turso_arg(v)} for k, v in params.items()]

        payload = {
            "requests": [
                {"type": "execute", "stmt": stmt}
            ]
        }

        res = self.conn._post_pipeline(payload)
        results = res.get("results", [])
        if not results:
            raise RuntimeError(f"Turso returned empty results for query: {sql}")

        first_res = results[0]
        if first_res.get("type") == "error":
            err = first_res.get("error", {})
            err_msg = err.get("message", "Unknown Turso Error")
            raise RuntimeError(f"Turso SQL Error: {err_msg} | Query: {sql}")

        resp_obj = first_res.get("response", {})
        result_data = resp_obj.get("result", {})

        cols = [c.get("name") for c in result_data.get("cols", [])]
        self.description = [(c, None, None, None, None, None, None) for c in cols]
        
        raw_rows = result_data.get("rows", [])
        parsed_matrix = [
            [_from_turso_value(cell) for cell in r]
            for r in raw_rows
        ]
        
        self._rows = [
            TursoRow(cols, row_vals)
            for row_vals in parsed_matrix
        ]
        self._row_idx = 0
        self.lastrowid = result_data.get("last_insert_rowid")
        self.rowcount = result_data.get("affected_row_count", 0)

        # Store in cache if read query
        if is_read_query and cache_key:
            _QUERY_CACHE[cache_key] = (time.time(), cols, parsed_matrix, self.lastrowid, self.rowcount)

        return self

    def executemany(self, sql: str, seq_of_params: List[Union[List, Tuple]]) -> "TursoCursor":
        total_affected = 0
        last_id = None
        for p in seq_of_params:
            self.execute(sql, p)
            total_affected += self.rowcount
            if self.lastrowid:
                last_id = self.lastrowid
        self.rowcount = total_affected
        self.lastrowid = last_id
        return self

    def fetchone(self) -> Optional[TursoRow]:
        if self._row_idx < len(self._rows):
            row = self._rows[self._row_idx]
            self._row_idx += 1
            return row
        return None

    def fetchall(self) -> List[TursoRow]:
        remaining = self._rows[self._row_idx:]
        self._row_idx = len(self._rows)
        return remaining

    def close(self):
        self._rows = []


class TursoConnection:
    def __init__(self, database_url: str, auth_token: str):
        clean_url = database_url.strip()
        if clean_url.startswith("libsql://"):
            clean_url = "https://" + clean_url[len("libsql://"):]
        elif not clean_url.startswith("https://") and not clean_url.startswith("http://"):
            clean_url = "https://" + clean_url
        
        clean_url = clean_url.rstrip("/")
        if not clean_url.endswith("/v2/pipeline"):
            self.endpoint = f"{clean_url}/v2/pipeline"
        else:
            self.endpoint = clean_url

        self.auth_token = auth_token.strip()
        self.row_factory = None
        self._client = _get_shared_client(self.auth_token)

    def _post_pipeline(self, payload: dict) -> dict:
        r = self._client.post(self.endpoint, json=payload)
        if r.status_code != 200:
            raise RuntimeError(f"Turso HTTP {r.status_code}: {r.text}")
        return r.json()

    def cursor(self) -> TursoCursor:
        return TursoCursor(self)

    def execute(self, sql: str, params: Optional[Union[List, Tuple, dict]] = None) -> TursoCursor:
        c = self.cursor()
        return c.execute(sql, params)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        # Do NOT close the shared HTTP client pool! Keep TCP/SSL connections warm!
        pass
