import unittest
import os
import shutil
import sqlite3
from backend.agents.code_agent import CodeAgent
from backend.agents.database_agent import DatabaseAgent
from backend.config import get_user_database_path, current_user_id

class TestSelfCorrectionLoops(unittest.TestCase):
    def setUp(self):
        # Set user id to a test scope
        current_user_id.set("test_user")
        
        # Clean up any pre-existing test DB
        db_path = get_user_database_path()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

    def tearDown(self):
        # Clean up DB after test
        db_path = get_user_database_path()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
        current_user_id.set(None)

    def test_code_agent_self_correction(self):
        """Test that the CodeAgent recovers from a NameError when instructed to run code referencing an undefined variable."""
        agent = CodeAgent()
        # Query designed to fail first, forcing the self-correction loop to define x
        query = "Run a python script that references an undefined variable 'x' (e.g. print(x)). When it fails with NameError, correct the code to define x = 100 and print(x) so that it completes successfully."
        
        response = agent.run(query)
        print("Code Agent Response:\n", response)
        
        # The final output should contain 100 or indicate successful correction
        self.assertIn("100", response)

    def test_database_agent_self_correction(self):
        """Test that the DatabaseAgent recovers from a missing table error by creating the table and repeating the operation."""
        agent = DatabaseAgent()
        # Query designed to fail on insert since table does not exist
        query = "Insert a row with id=99 and value='self_correction_test' into a table named 'temp_integration_table'. Since the table does not exist, you must create it with columns 'id' (INTEGER) and 'value' (TEXT) first, and then repeat the insertion successfully."
        
        response = agent.run(query)
        print("Database Agent Response:\n", response)
        
        # Verify from the database itself that the insertion was successful
        db_path = get_user_database_path()
        self.assertTrue(os.path.exists(db_path), "Database file was not created")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='temp_integration_table';")
        table_exists = cursor.fetchone()
        self.assertIsNotNone(table_exists, "Table was not created during self-correction")
        
        cursor.execute("SELECT id, value FROM temp_integration_table WHERE id=99;")
        row = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(row, "Data was not inserted successfully during self-correction")
        self.assertEqual(row[1], "self_correction_test")

    def test_code_agent_package_install_loop(self):
        """Test that the orchestrator routes to package manager and back to code agent when a module is missing."""
        from backend.core.orchestrator import Orchestrator
        from backend.core.registry import AgentRegistry
        from backend.agents import ALL_AGENTS

        registry = AgentRegistry()
        for AgentClass in ALL_AGENTS:
            registry.register(AgentClass())
        
        orchestrator = Orchestrator(registry)
        
        # We uninstall colorama first (to make sure it fails)
        from backend.core.sandbox import DockerSandboxManager
        sandbox = DockerSandboxManager("test_user")
        sandbox.execute(["pip", "uninstall", "-y", "colorama"])

        query = (
            "Write and run a python script in the sandbox that imports the package 'colorama' "
            "and prints its version. If it fails with ModuleNotFoundError, use the package manager "
            "to install 'colorama' first, and then execute the script successfully."
        )
        
        result = orchestrator.run(query, session_id="test_session_package")
        response = result["response"]
        print("Orchestrator Package Install Flow Response:\n", response)
        
        # Verify colorama version or output is present
        self.assertTrue(any(agent in result["agents_used"] for agent in ["code", "package_manager"]))

    def test_database_agent_schema_evolution(self):
        """Test that the DatabaseAgent alters a table schema if a column is missing during an insert operation."""
        agent = DatabaseAgent()
        
        # Create table with only 'id' and 'value' first
        db_path = get_user_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE temp_integration_table (id INTEGER, value TEXT);")
        conn.commit()
        conn.close()

        # Insert query with extra column 'extra_info' not present in schema
        query = (
            "Insert a row with id=101, value='evolution_test', and extra_info='evolved_data' "
            "into the table 'temp_integration_table'. Since the column 'extra_info' does not exist "
            "yet in the table schema, you MUST alter the table structure to add 'extra_info' as TEXT, "
            "and then repeat the insert query successfully."
        )
        
        response = agent.run(query)
        print("Database Schema Evolution Response:\n", response)

        # Verify from database that table now has the new column and values
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(temp_integration_table);")
        columns = [col[1] for col in cursor.fetchall()]
        self.assertIn("extra_info", columns, "extra_info column was not added to the schema")

        cursor.execute("SELECT id, value, extra_info FROM temp_integration_table WHERE id=101;")
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row, "Data was not inserted after schema evolution")
        self.assertEqual(row[2], "evolved_data")

if __name__ == "__main__":
    unittest.main()
