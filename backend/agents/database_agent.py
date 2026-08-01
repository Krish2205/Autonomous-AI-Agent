"""
JARVIS — Database Agent
SQLite file operations for structured data creation, insertion, and querying.
"""

import sqlite3
import sqlglot
import sqlglot.expressions as exp
from langchain_core.tools import tool
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from backend.agents.base import BaseAgent
from backend.config import llm, get_user_database_path
from backend.logger import get_logger

logger = get_logger("agents.database")


def validate_sql_ast(sql_query: str) -> None:
    """
    Parses the SQL statement into an AST using sqlglot and validates it against security policies:
    1. Blocks destructive schema changes (DROP, ALTER).
    2. Blocks access to system / metadata tables (e.g., sqlite_master, conversations).
    """
    try:
        expression = sqlglot.parse_one(sql_query, read="sqlite")
        
        # Traverse AST nodes
        for node in expression.walk():
            # Block DROP or ALTER commands
            if isinstance(node, (exp.Drop, exp.Alter)):
                raise PermissionError("Schema modification commands (DROP/ALTER) are blocked by the AST SQL Firewall.")
            
            # Block queries referencing system/sensitive tables
            if isinstance(node, exp.Table):
                table_name = node.name.lower()
                forbidden_tables = [
                    "profile_configs",
                    "conversations",
                    "document_chunks",
                    "sqlite_master",
                    "sqlite_sequence",
                    "sqlite_stat",
                ]
                if table_name in forbidden_tables:
                    raise PermissionError(f"Access to database system table '{table_name}' is blocked by the AST SQL Firewall.")
    except sqlglot.errors.ParseError as pe:
        raise ValueError(f"SQL Syntax / Parsing Error: {str(pe)}")


@tool
def execute_sql(sql_query: str) -> str:
    """
    Execute a raw SQLite SQL query (CREATE TABLE, INSERT INTO, SELECT, UPDATE, DELETE).
    Returns query result rows formatted as a markdown table, or a success message for write operations.
    """
    logger.info(f"Executing SQL query: {sql_query}")
    
    # Run AST Firewall validation
    try:
        validate_sql_ast(sql_query)
    except Exception as e:
        logger.warning(f"SQL query rejected by AST Firewall: {e}")
        return f"Error: SQL query rejected by AST Firewall. Reason: {str(e)}"

    try:
        conn = sqlite3.connect(get_user_database_path())
        cursor = conn.cursor()
        cursor.execute(sql_query)
        
        # Determine if it is a write command
        query_type = sql_query.strip().split()[0].upper()
        if query_type in ("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"):
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return f"Success: Query executed successfully. Affected rows: {affected if affected >= 0 else 0}."

        rows = cursor.fetchall()
        if not cursor.description:
            conn.close()
            return "Success: Query completed (no result columns)."

        columns = [desc[0] for desc in cursor.description]
        conn.close()

        if not rows:
            return "Query executed successfully, but returned 0 rows."

        # Format as markdown table
        header = " | ".join(columns)
        divider = " | ".join(["---"] * len(columns))
        rows_str = []
        for row in rows:
            rows_str.append(" | ".join(str(val) for val in row))
            
        return f"\n{header}\n{divider}\n" + "\n".join(rows_str) + "\n"

    except Exception as e:
        logger.error(f"SQL execution failed: {e}")
        return f"Error executing SQL: {str(e)}"


@tool
def get_db_schema() -> str:
    """
    Retrieve the names and schema column definitions for all user tables in the SQLite database.
    Always run this tool first if you do not know which tables exist.
    """
    logger.info("Retrieving database schema...")
    try:
        conn = sqlite3.connect(get_user_database_path())
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()
        if not tables:
            conn.close()
            return "The database is currently empty (contains 0 tables)."

        schema_info = []
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            cols_str = ", ".join(f"{col[1]} ({col[2]})" for col in columns)
            schema_info.append(f"- Table '{table_name}': {cols_str}")
        
        conn.close()
        return "Current Database Schema:\n" + "\n".join(schema_info)

    except Exception as e:
        logger.error(f"Schema retrieval failed: {e}")
        return f"Error retrieving schema: {str(e)}"


class DatabaseAgent(BaseAgent):
    name = "database"
    description = (
        "Query or write to the local SQLite database. "
        "Create tables, insert rows, update records, and run analytical queries for structured logs, lists, or metrics."
    )

    def __init__(self):
        self.tools = [get_db_schema, execute_sql]

    def run(self, query: str) -> str:
        logger.info(f"Running database task: {query[:80]}...")

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Principal Database Architect & SQL Optimization Engineer for JARVIS.\n"
                "You specialize in relational database schema design, ACID transactional integrity, complex SQL queries, and dynamic schema migrations for SQLite.\n\n"
                "<execution_guidelines>\n"
                "1. Always inspect target table structures via `get_db_schema` before executing writes or complex joins.\n"
                "2. Execute SQL statements using `execute_sql` adhering strictly to SQLite dialect constraints.\n"
                "3. SELF-CORRECTION MANDATE: If `execute_sql` returns an error, analyze the SQLite exception (e.g. missing column, syntax error, missing table), run dynamic schema migrations (`CREATE TABLE`, `ALTER TABLE`) if required, and re-execute the transaction successfully.\n"
                "4. Render all tabular query outputs as clean, beautifully formatted Markdown tables.\n"
                "</execution_guidelines>",
            ),
            ("human", "{query}"),
            ("placeholder", "{agent_scratchpad}"),
        ])

        agent = create_tool_calling_agent(llm=llm, tools=self.tools, prompt=prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True
        )

        try:
            response = executor.invoke({"query": query})
            result = response.get("output", str(response))
            logger.info("Database task completed successfully.")
            return result
        except Exception as e:
            logger.error(f"Database agent failed: {e}", exc_info=True)
            return f"Database error: {str(e)}"
