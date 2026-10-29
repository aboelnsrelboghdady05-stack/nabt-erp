import os
import httpx
import base64
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
        
        # Handle SQLite PRAGMA statements gracefully
        if sql_stripped.upper().startswith("PRAGMA"):
            # If PRAGMA table_info(tbl)
            if "table_info" in sql_stripped.lower():
                pass # let it run
            else:
                self._rows = []
                self.description = []
                self.lastrowid = None
                self.rowcount = 0
                return self

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
        self._rows = [
            TursoRow(cols, [_from_turso_value(cell) for cell in r])
            for r in raw_rows
        ]
        self._row_idx = 0
        self.lastrowid = result_data.get("last_insert_rowid")
        self.rowcount = result_data.get("affected_row_count", 0)
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
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

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
        try:
            self._client.close()
        except Exception:
            pass
