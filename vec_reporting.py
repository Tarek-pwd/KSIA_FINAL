import os
import pdfplumber
from fpdf import FPDF
from vectara_agentic.tools import ToolsFactory
from vectara_agentic.agent import Agent
from pydantic import BaseModel, Field

# Set your Vectara credentials
VECTARA_API_KEY = os.getenv('VECTARA_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

TEMPLATE_DIR = "my_templates"

# Global variables
template_dict = {}
filename_to_key = {}
key_to_filename = {}
_agent = None  # Store agent instance

def list_available_templates():
    return [f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".pdf")]

def extract_pdf_text(path):
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

def process_templates():
    available = list_available_templates()
    
    for filename in available:
        path = os.path.join(TEMPLATE_DIR, filename)
        key = f"template_{available.index(filename)}"
        template_dict[key] = extract_pdf_text(path)
        filename_to_key[filename] = key
        key_to_filename[key] = filename

def choose_report_template(
    report_name: str = Field(description="The exact name of the report template to select (including .pdf extension)")
) -> str:
    """Retrieves the text content of the selected template"""
    template_key = filename_to_key.get(report_name)
    if template_key:
        return template_dict[template_key]
    return f"Template '{report_name}' not found"

def create_assistant_tools():
    tools_factory = ToolsFactory()
    return [tools_factory.create_tool(choose_report_template)]

def get_agent():
    """Get or create the singleton agent instance"""
    global _agent
    
    if _agent is None:
        template_list = "\n".join([f"- {name}" for name in filename_to_key.keys()])
        
        instructions = f"""You are an Arabic document assistant. You must ALWAYS respond in Arabic.

Available templates:
{template_list}

Your task:
1. Understand what the user needs from their query
2. Choose the most appropriate template from the available list
3. Call the choose_report_template tool with the exact template name INCLUDING the .pdf extension
4. Once you receive the template text, fill it with the information provided by the user
5. Keep the original template format and structure
6. Replace only the blank fields with user's information
7. Add a formal closing paragraph explaining the purpose of this request

Remember: All your responses must be in Arabic, but you understand instructions in English."""
        
        _agent = Agent(
            tools=create_assistant_tools(),
            topic="Arabic Report Templates Assistant",
            custom_instructions=instructions,
            verbose=True
        )
        print("-------- Agent created --------")
    
    return _agent

# Initialize templates when module is loaded
process_templates()
print("-------- Templates processed --------")

def run_query(user_query):
    """Run a query using the persistent agent"""
    agent = get_agent()
    result = agent.chat(user_query)
    return str(result)

def reset_agent():
    """Reset the agent to start a new conversation"""
    global _agent
    _agent = None
    print("-------- Agent reset --------")