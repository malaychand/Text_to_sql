from langchain_community.chat_models import ChatHuggingFace
from langchain_community.llms import HuggingFaceEndpoint
import re

llm = HuggingFaceEndpoint(
    repo_id="HuggingFaceH4/zephyr-7b-beta",
    task="text-generation",
    temperature=0.7,
    max_new_tokens=256,
    top_p=0.95,
)

model = ChatHuggingFace(llm=llm)

def convert_to_sql(natural_query, table_schema, df_head):
    prompt = f"""
You are an AI assistant that converts natural language into precise SQL queries compatible with DuckDB.

Table name: df  
Schema: {table_schema}

please check Sample data (first 2 rows):
{df_head}

Please check schema and sample data carefully before generating SQL.
Assume:
- All column names are lowercase.
- All string values are trimmed of whitespace and lowercased.
- The words 'clients' and 'rows' can be refer to records.
- Only use the table name 'df'.

Convert the following natural language question into a SQL query:
\"{natural_query}\"

Only return the SQL query.
"""
    response = model.invoke(prompt)
    sql = response.content.strip()
    sql = re.sub(r"[`\"]", "", sql)
    sql = re.sub(r"\bfrom\s+\w+", "FROM df", sql, flags=re.IGNORECASE)
    return sql
