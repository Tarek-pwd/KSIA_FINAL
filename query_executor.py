
"""
Subprocess executor for Vectara queries
This runs in a completely separate process to avoid state conflicts -- 
"""

import sys
import json
from vectara_agentic.tools import VectaraToolFactory
from vectara_agentic.agent import Agent
from pydantic import Field, BaseModel
import os

schema_markdown = '''# HR Database Schema
## Tables

### `employees` *merges Employee, Department, Legal* columns:
- `emp_id` (PK INT AUTO_INCREMENT) → unique identifier for each employee  
- `first_name` (VARCHAR(50) NOT NULL) → first name of employee
- `last_name` (VARCHAR(50) NOT NULL) → last name of employee
- `phone` (VARCHAR(20)) → contact phone number of employee
- `email` (VARCHAR(100) UNIQUE) → unique email address of employee
- `nationality` (VARCHAR(50)) → employee nationality  
- `flight_cost` (DECIMAL(12,2)) → cost associated with business travel for each employee
- `iqama_expiry_date` (DATE) → residency permit expiry date for each employee
- `hiring_date` (DATE NOT NULL) → date employee was hired  
- `gender` (ENUM('Male','Female')) → employee gender. Distinct values include ['Male','Female']  
- `dob` (DATE NOT NULL) → date of birth of employee
- `job_position` (VARCHAR(100)) → current job title of employee
- `status` (ENUM('Active','Inactive','Terminated') DEFAULT 'Active') → employment status of each employee. Distinct values include ['Active','Inactive','Terminated']  
- `manager_id` (INT) → id of manager managing each employee. Foreign key to Employee.emp_id for direct manager  
- `department` (ENUM('HR','IT','Marketing','Operations','Sales') NOT NULL) → department name of each employee. Distinct values include ['HR','IT','Marketing','Operations','Sales']  
- `contract_type` (ENUM('Definite','Indefinite') NOT NULL) → contract type of each employee. Distinct values include ['Definite','Indefinite']  
- `actual_wage` (DECIMAL(12,2) NOT NULL) → wage of each employee used for end of service calculation  
- `years_service` (INT DEFAULT 0) → years of service of each employee
- `months_service` (INT DEFAULT 0) → months of service of each employee  
- `days_service` (INT DEFAULT 0) → days of service of each employee
- `termination_reason` (ENUM(
  'Resignation',
  'The termination of the contract by the employer for an unlawful reason',
  'Death of the employee',
  'Termination of the contract pursuant Article (81)',
  'Agreement to Terminate'
)) → reason for termination for each employee. Distinct values include ['Resignation', 'The termination of the contract by the employer for an unlawful reason', 'Death of the employee', 'Termination of the contract pursuant Article (81)', 'Agreement to Terminate']

### `salaries` *merges Salary_Current, Salary_History* columns:
- `emp_id` (PK INT) → id of each employee which is foreign key to Employee.emp_id  
- `salary_2022` (DECIMAL(12,2)) → salary of each employee for year 2022
- `salary_2023` (DECIMAL(12,2)) → salary of each employee for year 2023  
- `salary_2024` (DECIMAL(12,2)) → salary of each employee for year 2024  
- `base_salary_2025` (DECIMAL(12,2) NOT NULL) → base salary of each employee for year 2025  
- `housing_allowance_2025` (DECIMAL(12,2) DEFAULT 0) → housing allowance of each employee for year 2025  
- `transport_allowance_2025` (DECIMAL(12,2) DEFAULT 0) → transport allowance of each employee for year 2025  
- `total_salary_2025` (DECIMAL(12,2) STORED) → total salary of each employee computed as base_salary_2025 + housing_allowance_2025 + transport_allowance_2025

### `attendance` *merges Attendance, Leaves, Yearly_Absences* columns:
- `attendance_id` (PK INT AUTO_INCREMENT) → unique attendance record id  
- `emp_id` (INT NOT NULL) → id of each employee which is foreign key to Employee.emp_id  
- `att_date` (DATE) → attendance date for each employee
- `check_in` (DATETIME) → checkin timestamp for each employee for that att_date 
- `check_out` (DATETIME) → checkout timestamp for each employee for that att_date
- `attendance_status` (ENUM('Present','Absent','On Leave') NOT NULL DEFAULT 'Present') → attendance status of each employee. Distinct values include ['Present','Absent','On Leave']  
- `leave_type` (ENUM('Sick','Holiday','Maternity')) → leave type for each employee if they are "Absent" or "On Leave". Distinct values include ['Sick','Holiday','Maternity']  
- `allocated_days` (INT) → leave days allocated for employee leave
- `used_days` (INT DEFAULT 0) → leave days used by employee
- `remaining_days` (INT VIRTUAL) → leave days left for employee computed as allocated_days minus used_days  
- `leave_status` (ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending') → leave approval status for employee. Distinct values include ['Pending','Approved','Rejected']  
- `yearly_absence_2022` (INT CHECK (yearly_absence_2022 BETWEEN 0 AND 22)) → absences of each employee in year 2022. Distinct values range from 0 to 22  
- `yearly_absence_2023` (INT CHECK (yearly_absence_2023 BETWEEN 0 AND 22)) → absences of each employee in year 2023. Distinct values range from 0 to 22  
- `yearly_absence_2024` (INT CHECK (yearly_absence_2024 BETWEEN 0 AND 22)) → absences of each employee in year 2024. Distinct values range from 0 to 22

### `rating` *stores annual performance ratings* columns:
- `rate_id` (PK INT AUTO_INCREMENT) → unique rating record id  
- `emp_id` (INT NOT NULL) → id of each employee which is foreign key to Employee.emp_id  
- `rate_2022` (INT CHECK (rate_2022 BETWEEN 1 AND 5)) → rating of each employee in year 2022. Distinct values include [1,2,3,4,5]  
- `rate_2023` (INT CHECK (rate_2023 BETWEEN 1 AND 5)) → rating of each employee in year 2023. Distinct values include [1,2,3,4,5]  
- `rate_2024` (INT CHECK (rate_2024 BETWEEN 1 AND 5)) → rating of each employee in year 2024. Distinct values include [1,2,3,4,5]

### `extras` *merges Benefits, Debt* columns:
- `extras_id` (PK INT AUTO_INCREMENT) → unique extras record id  
- `emp_id` (INT NOT NULL) → employee id which is foreign key to Employee.emp_id  
- `healthcare_insurance_class` (VARCHAR(50)) → health plan classification for each employee 
- `healthcare_insurance_type` (ENUM('Medgulf','Tawuniya','Bupa')) → insurance provider for each employee. Distinct values include ['Medgulf','Tawuniya','Bupa']  
- `childcare_insurance` (BOOLEAN DEFAULT FALSE) → childcare coverage eligibility for each employee 
- `car` (BOOLEAN DEFAULT FALSE) → company car eligibility for each employee
- `gadgets` (ENUM('laptop','phone','tablet')) → provided gadget for each employee. Distinct values include ['laptop','phone','tablet']  
- `housing` (BOOLEAN DEFAULT FALSE) → housing allowance eligibility for each employee
- `total_debt` (DECIMAL(14,2)) → total debt amount for each employee 
- `remaining_debt` (DECIMAL(14,2)) → remaining debt balance for each employee
- `debt_date` (DATE) → debt record date for each employee
- `due_date` (DATE) → debt due date for each employee
- `debt_status` (ENUM('Pending','Paid','Overdue') DEFAULT 'Pending') → debt status for each employee. Distinct values include ['Pending','Paid','Overdue']  
- `payment_per_month` (DECIMAL(12,2)) → scheduled monthly payment for reach employee  
- `interest_rate` (DECIMAL(5,2)) → annual interest rate percent for each employee

### `projects_experience` *merges Projects, Experience* columns:
- `proj_exp_id` (PK INT AUTO_INCREMENT) → unique projectsexperience record id  
- `emp_id` (INT NOT NULL) → employee id which is foreign key to Employee.emp_id  
- `project_name` (VARCHAR(150)) → project name of employee
- `start_date` (DATE) → project start date of employee
- `end_date` (DATE) → project end date of employee
- `project_status` (ENUM('Planned','Active','Completed','On Hold') DEFAULT 'Planned') → project state of employee. Distinct values include ['Planned','Active','Completed','On Hold']  
- `budget` (DECIMAL(14,2)) → project budget of employee
- `previous_employer` (VARCHAR(150)) → past employer name of employee
- `previous_role` (VARCHAR(100)) → past job title of employee
- `exp_years` (INT) → years of prior experience of employee

## Relationships

1. `employees.manager_id` → `employees.emp_id`  
2. `salaries.emp_id` → `employees.emp_id`  
3. `attendance.emp_id` → `employees.emp_id`  
4. `rating.emp_id` → `employees.emp_id`  
5. `extras.emp_id` → `employees.emp_id`  
6. `projects_experience.emp_id` → `employees.emp_id`  
'''



def execute_query(query):
    try:
        # Create Vectara components
        vec_factory = VectaraToolFactory(
            vectara_api_key='zut_260-TfMw7QwpbtL5lrro3KUOaJGS-i3QbU8XFg',
            vectara_corpus_key='HR_demo'
        )
        
        class QueryHRArgs(BaseModel):
            query: str = Field(..., description="The user query.")
        
        query_hr = vec_factory.create_rag_tool(
            tool_name="query_hr_database",
            tool_description="Query the content from HR data",
            tool_args_schema=QueryHRArgs,
            reranker="multilingual_reranker_v1", 
            rerank_k=3,
            n_sentences_before=1,
            n_sentences_after=1,
            lambda_val=0.005,
            summary_num_results=10,
            vectara_summarizer='vectara-summary-table-md-query-ext-jan-2025-gpt-4o',
            include_citations=False,
            verbose=False
        )

        ## subsequential workflow

        
        agent_instructions = f"""
        - You are a an expert PostgreSQL assistant that generates prompts based on the schema markdown.
        - Thew database you are creating queries for is employyes datra consiting of many tables 
        - Be sure to give statemnts that would combine different tables together when needed
        - use the CURRENTDATE if you want to get the today's date
        - The schema Markdown is {schema_markdown}
        - Your answer should only be SQL statement and in postgreSQL syntax that would allow the user to fetch the corresponding data by executing the statement you will give.
        - Use the RAG tool to get matching chunks to give you more information for exmpale if the user entered a wrong name , the rag matched can let you understand that and generate the correct statement, but your task is still to generate the postgresSQL statament so never forget that
        - You must use a first name and last name in the query that was matched by the RAG tool strictly
        - even if RAG did not give any matches , you should still generate the postgreSQL statment
        - the answer should start with the word 'sql' and always be  a valid sql statament .  This is strict because it will be passed to a sql engine'
        - Even if the answer is something like 'Hello! How can I assist you with your HR database queries today?' you should give it as "sql select 'hello ....'"
        - If you are given more than one question they will be structured , so I will tell you which is which
        - In the case of more than one  question , generate a seperate SQL statement for every question please and as mentioned , the world 'sql' should always be before every reponse 
        """
        
        agent = Agent(
            tools=[query_hr],
            topic="SQL query generator",
            custom_instructions=agent_instructions,
            verbose=False
        )
        
        response = agent.chat(query)
        return {"status": "success", "response": str(response)}
        
    except Exception as e:
        return {"status": "error", "response": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "response": "No query provided"}))
        sys.exit(1)
    
    query = sys.argv[1]
    result = execute_query(query)
    print(json.dumps(result))