import os
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = os.getenv("SQLITE_PATH", "./data/trace.db")
GRAPH_JSON_PATH = os.getenv("GRAPH_JSON_PATH", "./data/graph.json")