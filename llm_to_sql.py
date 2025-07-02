# # llm_to_sql.py
# import re
# import os
# from langchain_openai import ChatOpenAI
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from dotenv import load_dotenv

# load_dotenv()
# openai_api_key = os.getenv("OPENAI_API_KEY")

# llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, openai_api_key=openai_api_key)

# prompt_template = ChatPromptTemplate.from_messages([
#     ("system", "You are an assistant that generates only SQL queries for DuckDB."),
#     ("user", "{full_prompt}")
# ])

# output_parser = StrOutputParser()
# sql_chain = prompt_template | llm | output_parser

# def generate_sql_from_prompt(full_prompt: str) -> str:
#     try:
#         raw_sql = sql_chain.invoke({"full_prompt": full_prompt})
#         return re.sub(r"[`\"]", "", raw_sql.strip())
#     except Exception as e:
#         return f"-- Error generating SQL: {e}"

# llm_to_sql.py


import os
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
import re

# ✅ Load API key from .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# ✅ Create OpenAI client
client = OpenAI(api_key=api_key)

def generate_sql_from_prompt(full_prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant that generates only SQL queries for DuckDB. Do not explain, only return the SQL."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0,
        )

        # ✅ Get and sanitize the SQL query
        sql = response.choices[0].message.content.strip()

        # ✅ Clean: remove semicolons and quotes/backticks
        sql = re.sub(r"[`\";]", "", sql)

        return sql

    except OpenAIError as e:
        return f"-- Error generating SQL: {e}"
