import datetime
from typing import List
from langchain_core.tools import tool

@tool
def get_current_time():
    """Returns the current system date and time."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool
def legal_calculator(expression: str):
    """
    Performs complex mathematical calculations (e.g., interest rates, 
    damages, dates). Input should be a math expression.
    """
    try:
        # Using a restricted eval or simple math logic for safety
        return str(eval(expression, {"__builtins__": None}, {"abs": abs, "round": round}))
    except Exception as e:
        return f"Calculation Error: {str(e)}"

@tool
def weather_lookup(location: str):
    """
    Checks historical or current weather for a specific location. 
    Crucial for case evidence (e.g., visibility, road conditions).
    """
    # Placeholder for OpenWeatherMap API
    return f"Weather for {location}: 22°C, Clear Skies (Simulated)"

@tool
def internet_search(query: str):
    """
    SEARCH GATEKEEPER: Only used for verifying live updates or 
    filling critical gaps. Not for searching books Aegis doesn't have.
    """
    return f"Search result for '{query}': No recent news found (Simulated)"

# --- Placeholder Stubs for Future Implementation ---
@tool
def legal_citation_formatter(text: str):
    """[PLACEHOLDER] Formats citations into Bluebook standards."""
    return "Tool Inactive: Requires implementation."

@tool
def statute_of_limitations_calc(jurisdiction: str, case_type: str):
    """[PLACEHOLDER] Calculates legal deadlines based on jurisdiction."""
    return "Tool Inactive: Requires implementation."

@tool
def conflict_checker(entities: List[str]):
    """[PLACEHOLDER] Checks for conflicts of interest in the vault."""
    return "Tool Inactive: Requires implementation."

@tool
def financial_intelligence_fetcher(ticker: str):
    """[PLACEHOLDER] Fetches live corporate financial data."""
    return "Tool Inactive: Requires implementation."

@tool
def legal_language_translator(text: str, target_lang: str):
    """[PLACEHOLDER] Translates legal text while maintaining context."""
    return "Tool Inactive: Requires implementation."

# Export the list of tools for the agent
utility_tools = [
    get_current_time, 
    legal_calculator, 
    weather_lookup, 
    internet_search, 
    legal_citation_formatter,
    statute_of_limitations_calc,
    conflict_checker,
    financial_intelligence_fetcher,
    legal_language_translator
]
