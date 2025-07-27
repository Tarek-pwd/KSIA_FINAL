#!/usr/bin/env python3
"""
Vectara Agent with proper streaming implementation
"""
import sys
import json
import os
import asyncio
from typing import Iterator, Any
from vectara_agentic.tools import VectaraToolFactory
from vectara_agentic.agent import Agent
from pydantic import Field, BaseModel
import time

 
def execute_query_with_streaming(query ,  flg):

    ### flg of 1 would execute the second set of instructions!

    
    agent_instructions_1 = """
    - You are an Expert room data violation assistant. You are given a file containing requirements (RULES_FILE) which you should compare against detection data.
    - Compare EVERY SINGLE rule in the RULES_FILE to the data in described_rooms.docx (the actual detections from the apartment).
    - For EVERY SINGLE requirement in the REQUIREMENTS_FILE, provide a compliance check in this EXACT format:
    
    REQUIREMENT: [Name of the requirement]
    STATUS: [PASS/VIOLATION/UNCLEAR]
    REASON: [Brief explanation why it passed/failed/unclear]
    ---
    
    Guidelines:
    1. Check EVERY requirement mentioned in the REQUIREMENTS_FILE
    2. Use STATUS: PASS if the requirement is met
    3. Use STATUS: VIOLATION if the requirement is not met
    4. Use STATUS: UNCLEAR if you cannot determine compliance
    5. Keep REASON brief and specific
    6. Always use the exact format above with '---' as separator
    7. Do not add any text outside this format
    """

    agent_instructions_2 = """
    - You are an Expert report generator base on data that you will get
    - The report  you will be generating is a smart report based on the employees you think that will leave the company
    - you will be given sql statements and their corresponding results to undersrand exactl ewhat is going on 
    - THe criteria that you should base you r assumptions on are three things that you will learn from the fed data
    - generate a smart report explaining exactly what is happening
    """
    agent_instructions = agent_instructions_1
    if flg:
        agent_instructions = agent_instructions_2
    
    agent_config = {
        'tools': [],
        'topic': "Apartment Detections to Rules comparison",
        'custom_instructions': agent_instructions,
        'verbose': False
    }
    

    agent = Agent(**agent_config)

    response = agent.chat(query)
    response_text = str(response)
        
    chunk_size = 10  
    for i in range(0, len(response_text), chunk_size):
        chunk = response_text[i:i + chunk_size]
        yield chunk
        time.sleep(0.02)

  
    

