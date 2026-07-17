"""
SQLiteStore: persists pipeline run results to SQLite for thesis evaluation.
Uses LLM to infer exact table schema from CSV structure.
"""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import hydra
import pandas as pd
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from agentteam.models.structured_outputs import SQLTableSchema

logger = logging.getLogger(__name__)


class SQLiteStore:
    """
    Persists pipeline outputs to SQLite.
    LLM infers table schema from CSV structure.
    Called once after pipeline completion — never inside the graph.
    """

    def __init__(self, db_path: Path, llm: BaseChatModel):
        self.db_path = db_path
        self.llm = llm
        self._schema_cache: dict[str, SQLTableSchema] = {}
        self._init_metadata_schema()
        self.cfg = self._load_configs()

    def _load_configs(self):
        """Load SQLiteStore configuration from Hydra."""
        with hydra.initialize(version_base=None, config_path="../../../configs"):
            logger.info("Loading SQLiteStore config...")
            cfg = hydra.compose(
                config_name="config",
                overrides=["storage/sqlite_store=default"],
            )
            logger.info("SQLiteStore config loaded successfully")
            return cfg.storage.sqlite_store

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _init_metadata_schema(self) -> None:
        """Create fixed metadata tables — these never change."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    run_id          TEXT PRIMARY KEY,
                    started_at      TEXT,
                    completed_at    TEXT,
                    status          TEXT,
                    files_processed INTEGER DEFAULT 0,
                    repair_attempts INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS repair_log (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id            TEXT NOT NULL,
                    repair_target     TEXT,
                    attempt_number    INTEGER,
                    success           INTEGER,
                    error_description TEXT,
                    repaired_at       TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
                );

                CREATE TABLE IF NOT EXISTS inferred_schemas (
                    table_name      TEXT PRIMARY KEY,
                    source_filename TEXT,
                    schema_json     TEXT,
                    inferred_at     TEXT
                );
            """)
        logger.info(f"Metadata schema initialised: {self.db_path}")

    def _infer_schema(self, df: pd.DataFrame, filename: str) -> SQLTableSchema:
        """Use LLM to infer SQL schema from DataFrame structure."""
        stem = Path(filename).stem
        table_name = stem.replace("-", "_").replace(" ", "_").lower()

        if table_name in self._schema_cache:
            logger.info(f"Schema cache hit: {table_name}")
            return self._schema_cache[table_name]

        sample = df.head(5).to_string(index=False)
        dtypes = df.dtypes.to_string()
        nulls = df.isnull().sum().to_string()

        schema_llm = self.llm.with_structured_output(SQLTableSchema)

        schema: SQLTableSchema = schema_llm.invoke(
            [
                HumanMessage(
                    content=(
                        self.cfg.persistance_prompt.format(
                            filename=filename,
                            table_name=table_name,
                            sample=sample,
                            dtypes=dtypes,
                            nulls=nulls,
                        )
                    )
                )
            ]
        )

        self._schema_cache[table_name] = schema
        self._save_schema_to_db(schema)
        logger.info(f"Schema inferred for {filename}: {len(schema.columns)} columns")
        return schema

    def _save_schema_to_db(self, schema: SQLTableSchema) -> None:
        """Persist inferred schema to inferred_schemas table for auditing."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO inferred_schemas
                    (table_name, source_filename, schema_json, inferred_at)
                VALUES (?, ?, ?, ?)
            """,
                (
                    schema.table_name,
                    schema.source_filename,
                    schema.model_dump_json(),
                    self._now(),
                ),
            )

    def _build_create_table_sql(self, schema: SQLTableSchema, layer: str) -> str:
        """Build CREATE TABLE SQL from inferred schema. Layer is 'silver' or 'quarantine'."""
        table_name = f"{layer}_{schema.table_name}"
        col_defs = []

        for col in schema.columns:
            definition = f"{col.column_name} {col.sql_type}"
            if not col.nullable:
                definition += " NOT NULL"
            col_defs.append(definition)

        col_defs.extend(
            [
                "run_id TEXT NOT NULL",
                "persisted_at TEXT NOT NULL",
            ]
        )

        if layer == "quarantine":
            col_defs.append("quarantine_reason TEXT")

        cols_sql = ",\n    ".join(col_defs)
        return f"CREATE TABLE IF NOT EXISTS {table_name} (\n    {cols_sql}\n);"

    def _ensure_table(self, schema: SQLTableSchema, layer: str) -> str:
        """Create table if not exists. Returns table name."""
        table_name = f"{layer}_{schema.table_name}"
        create_sql = self._build_create_table_sql(schema, layer)
        with self._connect() as conn:
            conn.execute(create_sql)
        return table_name

    def persist_run(
        self,
        run_id: str,
        started_at: str,
        status: str,
        files_processed: int,
        repair_attempts: int,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_runs
                    (run_id, started_at, completed_at, status, files_processed, repair_attempts)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    completed_at    = excluded.completed_at,
                    status          = excluded.status,
                    files_processed = excluded.files_processed,
                    repair_attempts = excluded.repair_attempts
            """,
                (
                    run_id,
                    started_at,
                    self._now(),
                    status,
                    files_processed,
                    repair_attempts,
                ),
            )
        logger.info(f"Run persisted: {run_id} — {status}")

    def persist_silver(self, run_id: str, filename: str, silver_path: Path) -> int:
        """Infer schema and write silver rows to a typed table."""
        if not silver_path.exists():
            logger.warning(f"Silver file not found: {silver_path}")
            return 0

        df = pd.read_csv(silver_path, encoding="utf-8")
        schema = self._infer_schema(df, filename)
        table_name = self._ensure_table(schema, "silver")
        now = self._now()

        col_names = [c.column_name for c in schema.columns] + ["run_id", "persisted_at"]
        placeholders = ", ".join(["?"] * len(col_names))
        insert_sql = (
            f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({placeholders})"
        )

        rows = []
        for _, row in df.iterrows():
            values = [row.get(c.column_name) for c in schema.columns]
            values += [run_id, now]
            rows.append(values)

        with self._connect() as conn:
            conn.executemany(insert_sql, rows)

        logger.info(f"Silver persisted: {filename} → {table_name} — {len(rows)} rows")
        return len(rows)

    def persist_quarantine(
        self, run_id: str, filename: str, quarantine_path: Path
    ) -> int:
        """Infer schema and write quarantine rows to a typed table."""
        if not quarantine_path.exists():
            logger.warning(f"Quarantine file not found: {quarantine_path}")
            return 0

        df = pd.read_csv(quarantine_path, encoding="utf-8")
        data_cols = [c for c in df.columns if c != "quarantine_reason"]
        df_data = df[data_cols]

        schema = self._infer_schema(df_data, filename)
        table_name = self._ensure_table(schema, "quarantine")
        now = self._now()

        col_names = [c.column_name for c in schema.columns] + [
            "run_id",
            "persisted_at",
            "quarantine_reason",
        ]
        placeholders = ", ".join(["?"] * len(col_names))
        insert_sql = (
            f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({placeholders})"
        )

        rows = []
        for _, row in df.iterrows():
            values = [row.get(c.column_name) for c in schema.columns]
            values += [
                run_id,
                now,
                row.get("quarantine_reason", ""),
            ]
            rows.append(values)

        with self._connect() as conn:
            conn.executemany(insert_sql, rows)

        logger.info(
            f"Quarantine persisted: {filename} → {table_name} — {len(rows)} rows"
        )
        return len(rows)

    def persist_repair(
        self,
        run_id: str,
        repair_target: str,
        attempt_number: int,
        success: bool,
        error_description: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO repair_log
                    (run_id, repair_target, attempt_number, success, error_description, repaired_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    run_id,
                    repair_target,
                    attempt_number,
                    int(success),
                    error_description,
                    self._now(),
                ),
            )
        logger.info(f"Repair persisted: {repair_target} attempt {attempt_number}")

    def query_run_summary(self, run_id: str) -> dict:
        with self._connect() as conn:
            run = conn.execute(
                "SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            repairs = conn.execute(
                "SELECT COUNT(*) FROM repair_log WHERE run_id = ?", (run_id,)
            ).fetchone()[0]
        return {
            "run_id": run_id,
            "status": run["status"] if run else "unknown",
            "files_processed": run["files_processed"] if run else 0,
            "repair_attempts": repairs,
        }

    def run_persistance(
        self,
        workspace_path: Path,
        repair_attempts: int,
        repaired_data: dict,
        run_id: str,
        started_at: str,
    ) -> None:
        """Persist the entire run to SQLite after pipeline completion."""
        silver_dir = workspace_path / "output" / "silver"
        quarantine_dir = workspace_path / "output" / "quarantine"

        self.persist_run(
            run_id=run_id,
            started_at=started_at,
            status="complete" if silver_dir.glob("*.csv") else "failed",
            files_processed=len(list(silver_dir.glob("*.csv"))),
            repair_attempts=repair_attempts,
        )

        for silver_path in silver_dir.glob("*.csv"):
            p = Path(silver_path)
            self.persist_silver(run_id, p.name, p)

        for quarantine_file in quarantine_dir.glob("*.csv"):
            self.persist_quarantine(run_id, quarantine_file.name, quarantine_file)

        if repaired_data:
            self.persist_repair(
                run_id=run_id,
                repair_target=repaired_data.get("script_path", "unknown"),
                attempt_number=repair_attempts,
                success=repaired_data.get("status") == "complete",
                error_description=str(repaired_data.get("errors", [])),
            )
