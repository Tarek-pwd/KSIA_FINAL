import subprocess
import json
import sys
import time
import logging
from query_database import execute_query

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def run_smart_query(query: str):
    print("user query is" , query) 
   
    try:
        logger.info(f"Processing query: {query}")
    
        # Add a small delay between queries
        time.sleep(0.5)
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, 'query_executor.py', query],
            capture_output=True,
            text=True,
            timeout=30  
        )
        end_time = time.time()
        logger.info(f"Query completed in {end_time - start_time:.2f} seconds")
        
        if result.returncode != 0:
            logger.error(f"Subprocess error: {result.stderr}")
            return f"Error executing query: {result.stderr}"
        
        # Parse the JSON response
        try:
            response_data = json.loads(result.stdout)
            print("recieved respone data from stdout is " , response_data)
            if response_data['status'] == 'success':
                for i in range(10):
                    print("tHE THING WAS RECIEVED AS SUCCESS ") 
                response = response_data['response']
                print("recieved resposne +++++++++++++++++" , response)
                return response
                
            
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


