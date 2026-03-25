import argparse
import sys
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
import operator

class AgentState(TypedDict):
    prd_text: str
    epics: List[str]
    stories: List[str]

def pm_node(state: AgentState):
    print("Executing Product Manager Node...")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    
    prompt = f"Extract Epics and user stories from the following PRD:\n{state['prd_text']}"
    response = llm.invoke(prompt)
    
    # Mock processing
    new_stories = ["As a user, I want X so that Y", "As a admin, I want A so that B"]
    return {"epics": ["Core Authentication"], "stories": new_stories}

def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("pm", pm_node)
    builder.set_entry_point("pm")
    builder.add_edge("pm", END)
    return builder.compile()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", help="Pull request number containing the PRD")
    args = parser.parse_args()

    if not args.pr:
        print("Required --pr argument")
        sys.exit(1)

    print(f"Starting PM Agent for PR #{args.pr} using Google Gemini API")
    graph = build_graph()
    
    # Example execution (assuming prd text fetched from PyGithub)
    initial_state = {"prd_text": "# PRD\nWe need a login page.", "epics": [], "stories": []}
    
    # In reality, checkpoint saver would be passed to graph.invoke(..., config={"configurable": {...}})
    result = graph.invoke(initial_state)
    print("Agent output generated.")
    
    # Here the script opens a GitHub issue titled "Draft Backlog Review..."
    # using src/tools/github_client.py 

if __name__ == "__main__":
    main()
