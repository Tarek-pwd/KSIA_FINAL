import openai
from query_database import execute_query
from vec_agentic import clean_sql
import os
from dotenv import load_dotenv
load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

schema_markdown = '''# HR Database Schema

## Tables

### `employees` *contains basic employee information* columns:
- `emp_id` (PK, INT AUTO_INCREMENT) → unique identifier for each employee
- `first_name` (VARCHAR(50), NOT NULL) → employee first name
- `last_name` (VARCHAR(50), NOT NULL) → employee last name
- `phone` (VARCHAR(20)) → contact phone number
- `email` (VARCHAR(100), UNIQUE) → unique email address
- `nationality` (VARCHAR(50)) → employee nationality
- `flight_cost` (DECIMAL(12,2)) → cost associated with business travel
- `iqama_expiry_date` (DATE) → residency permit expiration date
- `hiring_date` (DATE, NOT NULL) → date the employee was hired
- `gender` (ENUM('Male','Female')) → employee gender. Distinct values include ['Male','Female']
- `dob` (DATE, NOT NULL) → date of birth
- `job_position` (VARCHAR(100)) → current job title
- `status` (ENUM('Active','Inactive','Terminated'), DEFAULT 'Active') → current employment status. Distinct values include ['Active','Inactive','Terminated']
- `manager_id` (INT, FK → Employee.emp_id) → the id of the direct manager of an employee
- `department_id` (INT, FK → Department.department_id) → the id of the department of an employee


### `departments` *contains department assignments for each employee* columns:
- `emp_id` (INT, PK, FK → Employee.emp_id) → id of the employee
- `department_id` (INT, UNIQUE, NOT NULL) → unique department identifier
- `name` (ENUM('HR','IT','Marketing','Operations','Sales'), NOT NULL) → the department name. Distinct values include ['HR','IT','Marketing','Operations','Sales']



### `attendance` *records daily attendance of days and check in check out timestamps for each employee* columns:
- `attendance_id` (PK, INT AUTO_INCREMENT) → unique attendance record id
- `emp_id` (INT, NOT NULL, FK → Employee.emp_id) → employee id
- `att_date` (DATE, NOT NULL) → date of attendance of an employee
- `check_in` (DATETIME) → check in timestamp of an employee
- `check_out` (DATETIME) → check out timestamp of an employee
- `status` (ENUM('Present','Absent','On Leave'), NOT NULL, DEFAULT 'Present') → attendance status of an employee. Distinct values include ['Present','Absent','On Leave']



### `leaves` *tracks leave allocations and usages for each employee* columns:
- `leaves_id` (PK, INT AUTO_INCREMENT) → unique leave record id
- `emp_id` (INT, NOT NULL, FK → Employee.emp_id) → employee id
- `leave_type` (ENUM('Sick','Holiday','Maternity'), NOT NULL) → type of leave. Distinct values include ['Sick','Holiday','Maternity']
- `allocated_days` (INT, NOT NULL) → total leave days allocated for each employee
- `used_days` (INT, NOT NULL, DEFAULT 0) → leave days used by each employee
- `remaining_days` (INT, VIRTUAL) → computed as allocated_days minus used_days for each employee
- `status` (ENUM('Pending','Approved','Rejected'), NOT NULL, DEFAULT 'Pending') → approval status for each employee. Distinct values include ['Pending','Approved','Rejected']


### `debts` *contains employee debts and repayment* columns:
- `debt_id` (PK, INT AUTO_INCREMENT) → unique debt record id
- `emp_id` (INT, NOT NULL, FK → Employee.emp_id) → employee id
- `total_debt` (DECIMAL(14,2), NOT NULL) → total debt amount for each employee
- `remaining_debt` (DECIMAL(14,2), NOT NULL) → remaining debt for each employee
- `debt_date` (DATE, NOT NULL) → date debt recorded for each employee
- `due_date` (DATE, NOT NULL) → debt due date for each employee
- `status` (ENUM('Pending','Paid','Overdue'), NOT NULL, DEFAULT 'Pending') → debt status for each employee. Distinct values include ['Pending','Paid','Overdue']
- `payment_per_month` (DECIMAL(12,2)) → scheduled monthly payment
- `interest_rate` (DECIMAL(5,2)) → annual interest rate percent for each employee


### `projects` *logs employee project assignments* columns:
- `project_id` (PK, INT AUTO_INCREMENT) → unique project record id
- `emp_id` (INT, NOT NULL, FK → Employee.emp_id) → employee id
- `project_name` (VARCHAR(150), NOT NULL) → name of the project the employee is working on  
- `start_date` (DATE, NOT NULL) → project start date
- `end_date` (DATE) → project end date
- `status` (ENUM('Planned','Active','Completed','On Hold'), NOT NULL, DEFAULT 'Planned') → project state for each employee. Distinct values include ['Planned','Active','Completed','On Hold']
- `budget` (DECIMAL(14,2)) → allocated budget for each project


### `experience` *contains prior work experience for each employee* columns:
- `experience_id` (PK, INT AUTO_INCREMENT) → unique experience record id
- `emp_id` (INT, NOT NULL, FK → Employee.emp_id) → employee id
- `previous_employer` (VARCHAR(150), NOT NULL) → past employer name for each employee
- `previous_role` (VARCHAR(100), NOT NULL) → past job title for each employee
- `exp_years` (INT, NOT NULL) → years of experience for each employee


### `benefits` *contains employee benefit selections* columns:
- `benefit_id` (PK, INT AUTO_INCREMENT) → unique benefit record id  
- `emp_id` (INT, NOT NULL, FK → Employee.emp_id) → employee id  
- `healthcare_insurance_class` (VARCHAR(50)) → health plan classification  
- `healthcare_insurance_type` (ENUM('Medgulf','Tawuniya','Bupa')) → insurance provider. Distinct values include ['Medgulf','Tawuniya','Bupa']  
- `childcare_insurance` (BOOLEAN, NOT NULL, DEFAULT FALSE) → childcare eligibility for each employee  
- `car` (BOOLEAN, NOT NULL, DEFAULT FALSE) → company car eligibility for each employee  
- `gadgets` (ENUM('laptop','phone','tablet')) → provided gadget for each employee. Distinct values include ['laptop','phone','tablet']  
- `housing` (BOOLEAN, NOT NULL) → housing allowance eligibility  for each employee


### `salaries` *contains salaries for each employee* columns:
- `salary_id` (PK, INT AUTO_INCREMENT) → unique salary record id
- `emp_id` (INT, NOT NULL, FK → Employee.emp_id) → employee id
- `base_salary` (DECIMAL(12,2), NOT NULL) → fixed salary amount for each employee
- `housing_allowance` (DECIMAL(12,2), DEFAULT 0) → housing component of the salary for each employee
- `transport_allowance` (DECIMAL(12,2), DEFAULT 0) → transport component of the salary for each employee
- `total_salary` (DECIMAL(12,2), STORED) → computed as base_salary plus housing_allowance plus transport_allowance



### `end_of_service` *contains end of service and contract details for each employee* columns:
- `eos_id` (PK, INT AUTO_INCREMENT) → unique end of service record id
- `emp_id` (INT, NOT NULL, FK → Employee.emp_id) → employee id
- `contract_type` (ENUM('Definite','Indefinite'), NOT NULL) → contract type. Distinct values include ['Definite','Indefinite']
- `actual_wage` (DECIMAL(12,2), NOT NULL) → final wage used for EOS calculation for each employee
- `years_service` (INT, DEFAULT 0) → years of service for each employee
- `months_service` (INT, DEFAULT 0) → months of service for each employee
- `days_service` (INT, DEFAULT 0) → days of service for each employee
- `termination_reason` (ENUM(
    'Resignation',
    'The termination of the contract by the employer for an unlawful reason',
    'Death of the employee',
    'Termination of the contract pursuant Article (81)',
    'Agreement to Terminate'
  ), NOT NULL) → reason for termination. Distinct values include ['Resignation','The termination of the contract by the employer for an unlawful reason','Death of the employee','Termination of the contract pursuant Article (81)','Agreement to Terminate']


### `salary_history` *contains annual salary history for each employee for three years* columns:
- `salary_id` (PK, INT AUTO_INCREMENT) → unique salary history record id  
- `emp_id` (INT, NOT NULL, FK → Employee.emp_id) → employee id  
- `salary_2022` (DECIMAL(12,2)) → salary for year 2022 for each employee
- `salary_2023` (DECIMAL(12,2)) → salary for year 2023  for each employee
- `salary_2024` (DECIMAL(12,2)) → salary for year 2024  for each employee

### `yearly_absences` *records yearly absence counts for three years per employee* columns:
- `absence_id` (PK, INT AUTO_INCREMENT) → unique absence record id  
- `emp_id` (INT, NOT NULL, FK → Employee.emp_id) → employee id  
- `absence_2022` (INT, CHECK (absence_2022 BETWEEN 0 AND 22)) → absences in 2022 for each employee. Distinct values range from 0 to 22  
- `absence_2023` (INT, CHECK (absence_2023 BETWEEN 0 AND 22)) → absences in 2023 for each employee. Distinct values range from 0 to 22  
- `absence_2024` (INT, CHECK (absence_2024 BETWEEN 0 AND 22)) → absences in 2024 for each employee. Distinct values range from 0 to 22  

### `employee_ratings` *stores annual performance ratings for three years per employee* columns:
- `rate_id` (PK, INT AUTO_INCREMENT) → unique rating record id  
- `emp_id` (INT, NOT NULL, FK → Employee.emp_id) → employee id  
- `rate_2022` (INT, CHECK (rate_2022 BETWEEN 1 AND 5)) → rating for 2022 for each emmployee. Distinct values include [1,2,3,4,5]  
- `rate_2023` (INT, CHECK (rate_2023 BETWEEN 1 AND 5)) → rating for 2023 for each employee. Distinct values include [1,2,3,4,5]  
- `rate_2024` (INT, CHECK (rate_2024 BETWEEN 1 AND 5)) → rating for 2024 for each employee. Distinct values include [1,2,3,4,5]  


## Relationships

1. Employee.manager_id → Employee.emp_id  
2. Employee.department_id → Department.department_id  
3. Department.emp_id → Employee.emp_id  
4. Attendance.emp_id → Employee.emp_id  
5. Leaves.emp_id → Employee.emp_id  
6. Debt.emp_id → Employee.emp_id  
7. Projects.emp_id → Employee.emp_id  
8. Experience.emp_id → Employee.emp_id  
9. Benefits.emp_id → Employee.emp_id  
10. Salary.emp_id → Employee.emp_id  
11. Legal.emp_id → Employee.emp_id
12. Salary_History.emp_id → Employee.emp_id  
13. Yearly_Absences.emp_id → Employee.emp_id  
14. Rating.emp_id → Employee.emp_id
'''
 
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
messages_arr = [{"role" : "system" , "content" : agent_instructions }]
def query_gpt(prompt):
    add_message("user",prompt)
    response = openai.chat.completions.create(
        model = 'gpt-4o',
        messages = messages_arr  
        )
    llm_reply = response.choices[0].message.content
    add_message('assistant',llm_reply)
    res = execute_query(clean_sql(llm_reply))
    print("the result is >> " , res)

    final_res = reasoning(messages_arr,res)
    return final_res
    
def add_message(poster,content):
    print("befpre messages arrayt >> " , messages_arr[1:])
    new_elem = {"role" : poster , "content" : content}
    messages_arr.append(new_elem)
    print("after appending  elem" , messages_arr[1:])



def reasoning(chat_history, current_answer):
    print("user last question" ,chat_history[-2])
    print("llm last reply" ,chat_history[-1])

    reasoning_instructions = """
another model beforeyou generated a  sql statement based on the user data . and then the code execurted the statemnt to get the result which is all numbers or
the results of sql queroes , you just need to take this as well as the answer and put in a sentence to be presented in a better way

sometimes a scenario would happen where the user would ask a normal uestion not realted to the SQL database , in which case the LLM repliy is something like 
sql select 'Hello! How can I assist you with your HR database queries today?' in such cases , just return the same answer the previous model got  which will be Hello! How can I assist you with your HR database queries today? in such case .
"""

    response = openai.chat.completions.create(
        model = 'gpt-4o', 
        messages = [
        {"role" : "system" , "content" : reasoning_instructions },
        {"role" : "user" , "content" : f"""the last user question was {chat_history[-2]['content']} . the last llm reply was {chat_history[-1]['content']} . 
         the current answer to the user's questions is {current_answer} now write your sentence based on all of these information please """}

    ])

    return response.choices[0].message.content



    


