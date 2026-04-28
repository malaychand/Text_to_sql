# llm_to_sql.py
from openai import OpenAI
import os

def generate_sql_from_prompt(prompt, api_key=None):
    """
    Generate SQL query from natural language prompt using OpenAI
    
    Args:
        prompt (str): The natural language prompt
        api_key (str, optional): OpenAI API key. If None, uses env var.
    
    Returns:
        str: Generated SQL query
    """
    # Use provided key or fallback to environment
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OpenAI API key not provided")
    
    # Clean the API key
    api_key = api_key.strip().strip('"').strip("'")
    
    client = OpenAI(api_key=api_key)
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4"
            messages=[
                {"role": "system", "content": "You are a SQL expert. Generate only valid SQL queries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=500
        )
        
        sql_query = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if sql_query.startswith("```sql"):
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        elif sql_query.startswith("```"):
            sql_query = sql_query.replace("```", "").strip()
        
        return sql_query
        
    except Exception as e:
        raise Exception(f"Error generating SQL: {str(e)}")