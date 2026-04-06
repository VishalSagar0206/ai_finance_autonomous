import subprocess
import tempfile
import os
import json
import logging
import sys

logger = logging.getLogger(__name__)

class LocalCodeExecutor:
    """
    Executes Python code in a controlled local subprocess.
    Extracts the 'BACKTEST_RESULTS:' JSON block from stdout.
    """

    @staticmethod
    def execute_python_code(code: str, timeout: int = 60) -> dict:
        """
        Writes code to a temp file, runs it, and parses JSON output.
        """
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w') as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            # Best Practice: Run with current python executable to ensure libraries (yfinance, pandas) are available
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                logger.error(f"Backtest execution failed: {result.stderr}")
                return {"status": "error", "error": result.stderr}

            # Search for the JSON result block in stdout
            output = result.stdout
            marker = "BACKTEST_RESULTS:"
            if marker in output:
                json_str = output.split(marker)[1].strip()
                return json.loads(json_str)
            
            return {"status": "error", "error": "No result marker found in output."}

        except subprocess.TimeoutExpired:
            logger.error("Backtest execution timed out.")
            return {"status": "error", "error": "Execution timed out."}
        except Exception as e:
            logger.error(f"Unexpected error in code execution: {str(e)}")
            return {"status": "error", "error": str(e)}
        finally:
            # Cleanup temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

code_executor = LocalCodeExecutor()
