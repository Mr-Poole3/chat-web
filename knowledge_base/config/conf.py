import os
import sys

_cur_dir = os.path.split(os.path.abspath(__file__))[0]
_prj_dir = os.path.split(_cur_dir)[0]
_root_dir = os.path.split(_prj_dir)[0]
sys.path.append(_root_dir)

DOMAIN = """Everything could be represented as a node (concept/entity)
For the connection between all these different nodes, there could be many edges (relationships).
Your task is to identify as many as possible for the entities (nodes) and the relationships (edges).
"""

EXAMPLE_QUERIES = [
    "How to qualify a lead effectively?",
    "What is the process for booking a meeting with a prospect?",
    "How to handle objections during a cold call?",
    "What are the best practices for email outreach?",
    "How to use CRM tools for lead tracking?",
]

ENTITY_TYPES = ["node"]
