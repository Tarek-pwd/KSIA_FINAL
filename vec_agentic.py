import subprocess
import json
import sys
import time
import logging
from query_database import execute_query

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Keep the schema_markdown for reference (not used in this file anymore)
schema_markdown = """# HR Database Schema
[Schema content here - truncated for brevity]
"""

def clean_sql(raw_text):
    if raw_text.strip().lower().startswith("sql"):
        return raw_text.strip()[3:].strip()  # remove 'sql' and any leading/trailing space
    return raw_text.strip()

def run_query(query: str):
    """Execute query in a separate subprocess to avoid state conflicts."""
    try:
        logger.info(f"Processing query: {query}")
        
        # Add a small delay between queries
        time.sleep(0.5)
        
        # Run the query in a subprocess
        start_time = time.time()
        
        result = subprocess.run(
            [sys.executable, 'query_executor.py', query],
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        end_time = time.time()
        logger.info(f"Query completed in {end_time - start_time:.2f} seconds")
        
        if result.returncode != 0:
            logger.error(f"Subprocess error: {result.stderr}")
            return f"Error executing query: {result.stderr}"
        
        # Parse the JSON response
        try:
            response_data = json.loads(result.stdout)
            if response_data['status'] == 'success':

                response = response_data['response']
                print("recieved resposne +++++++++++++++++" , response)
                executed_q_result = execute_query(clean_sql(response))
                print("final result",executed_q_result)
                return executed_q_result
            
            

            else:
                return f"Error: {response_data['response']}"
        except json.JSONDecodeError:
            logger.error(f"Failed to parse response: {result.stdout}")
            return "Error: Failed to parse query response"
            
    except subprocess.TimeoutExpired:
        logger.error("Query timed out")
        return "Query timed out. Please try again."
    except Exception as e:
        logger.error(f"Error in run_query: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

# Test function
def test_import():
    """Test function to verify the module imports correctly."""
    print("vec_agentic module loaded successfully")
    return True