import duckdb
import streamlit as st
import pandas as pd
import mysql.connector
import os
from dotenv import load_dotenv
from Mysql_extract_schema import get_mysql_schema
from csv_utils import detect_encoding, detect_delimiter  
from prompt_builder import build_prompt
from llm_to_sql import generate_sql_from_prompt

# Load environment variables
load_dotenv()

st.set_page_config(page_title="🧠 Text-to-SQL Tool", layout="wide")
st.title("🛠️ Natural Language to SQL Converter")

# ===============================#
# 🔹 Session State Initialization
# ===============================#
for key in ["uploaded_data", "file_prompts", "column_descriptions", 
            "dataframes", "table_descriptions", "delimiters", "schema_info", "db_creds"]:
    if key not in st.session_state:
        st.session_state[key] = {} if key != "db_creds" else {"host": "localhost", "user": "root", "password": ""}

# ===============================#
# 🔌 Sidebar: Configuration
# ===============================#
with st.sidebar:
    st.header("⚙️ Database & Tools")
    
    # 🔑 API Key Configuration
    st.subheader("🔑 OpenAI API Key")
    
    # Check if API key exists in environment
    env_api_key = os.getenv("OPENAI_API_KEY", "").strip().strip('"').strip("'")
    
    if env_api_key:
        st.success("✅ API key found in environment")
    else:
        st.warning("⚠️ No API key in environment")
    
    # API Key Input
    user_api_key = st.text_input(
        "API Key:",
        type="password",
        placeholder="sk-...",
        help="Enter your OpenAI API key (spaces and quotes will be auto-removed)"
    )
    
    # Clean the API key: trim spaces and remove quotes
    user_api_key = user_api_key.strip().strip('"').strip("'") if user_api_key else ""
    
    # Determine which API key to use (env has priority, but manual can override if provided)
    if user_api_key:
        api_key = user_api_key
        st.caption(f"🔐 Using manual key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '***'}")
    elif env_api_key:
        api_key = env_api_key
        st.caption(f"🔐 Using env key: {env_api_key[:8]}...{env_api_key[-4:]}")
    else:
        api_key = ""
        st.error("❌ API key required for NL→SQL")
    
    # Store in session state
    st.session_state["openai_api_key"] = api_key
    
    st.markdown("---")
    
    # 🗄️ MySQL Configuration
    st.subheader("🗄️ MySQL Connection")
    host = st.text_input("Host", value=st.session_state.db_creds["host"])
    user = st.text_input("Username", value=st.session_state.db_creds["user"])
    password = st.text_input("Password", type="password", value=st.session_state.db_creds["password"])
    
    st.session_state.db_creds = {"host": host, "user": user, "password": password}
    
    if st.button("🔗 Connect & Fetch Schema", type="primary"):
        with st.spinner("Connecting to MySQL..."):
            try:
                # Test connection first
                test_conn = mysql.connector.connect(host=host, user=user, password=password)
                test_conn.close()
                
                # Fetch schema
                schema_data = get_mysql_schema(host, user, password)
                st.session_state.schema_info = schema_data
                st.success("✅ Connected & Schema fetched!")
                
            except mysql.connector.Error as err:
                if err.errno == 2003:
                    st.error("❌ **Connection Refused (Error 2003)**\n"
                             "🔹 Ensure MySQL Server is running\n"
                             "🔹 Check if port 3306 is open")
                else:
                    st.error(f"❌ **MySQL Error:** `{err}`")
            except Exception as e:
                st.error(f"❌ **Unexpected Error:** `{e}`")
                
    if st.button("🗑️ Clear All Data"):
        for k in ["uploaded_data", "dataframes", "table_descriptions", "column_descriptions", "delimiters", "schema_info"]:
            st.session_state[k] = {}
        st.rerun()

# ===============================#
# 📤 1. CSV Upload & Annotation
# ===============================#
st.subheader("📁 Upload CSV Files")
with st.form(key="csv_upload_form"):
    uploaded_files = st.file_uploader("Choose CSV files", type="csv", accept_multiple_files=True)
    submit = st.form_submit_button("📤 Upload & Process")

if submit and uploaded_files:
    for file in uploaded_files:
        file_name = file.name.replace(".csv", "").strip()
        if file_name not in st.session_state.uploaded_data:
            try:
                encoding = detect_encoding(file)
                delimiter = detect_delimiter(file, encoding)
                df = pd.read_csv(file, delimiter=delimiter, encoding=encoding)

                st.session_state.uploaded_data[file_name] = df
                st.session_state.delimiters[file_name] = delimiter
                st.success(f"✅ Uploaded: `{file.name}` (Delimiter: `{delimiter}`)")
            except Exception as e:
                st.error(f"❌ Failed to load `{file.name}`: {e}")
        else:
            st.warning(f"⚠️ `{file.name}` already loaded. Skipping.")

# ===============================#
# 📂 2. MySQL Schema & Table Loader
# ===============================#
if "schema_info" in st.session_state and st.session_state.schema_info:
    st.subheader("🗄️ Load MySQL Tables")
    schema_data = st.session_state.schema_info
    
    selected_dbs = st.multiselect("Select Databases", list(schema_data.keys()))
    
    for db in selected_dbs:
        with st.expander(f"📦 `{db}`", expanded=True):
            tables = list(schema_data[db]["tables"].keys())
            selected_tables = st.multiselect(f"Tables in `{db}`", tables, key=f"sel_{db}")
            
            if selected_tables and st.button(f"📥 Load Tables from `{db}`", key=f"load_{db}"):
                with st.spinner("Fetching data from MySQL..."):
                    try:
                        conn = mysql.connector.connect(host=host, user=user, password=password, database=db)
                        cursor = conn.cursor(dictionary=True)
                        
                        for tbl in selected_tables:
                            cursor.execute(f"SELECT * FROM `{tbl}` LIMIT 10000")
                            rows = cursor.fetchall()
                            columns = [i for i in rows[0].keys()] if rows else []
                            df = pd.DataFrame(rows, columns=columns)
                            
                            st.session_state.dataframes[tbl] = df
                            st.session_state.table_descriptions[tbl] = schema_data[db]["tables"][tbl]["info"]
                        conn.close()
                        st.success(f"✅ Loaded {len(selected_tables)} table(s) from `{db}`")
                    except Exception as e:
                        st.error(f"❌ Failed to load tables: {e}")

# ===============================#
# 📊 3. Data Preview & Annotation
# ===============================#
st.subheader("📊 Loaded Tables")
all_tables = {**st.session_state.uploaded_data, **st.session_state.dataframes}

if not all_tables:
    st.info("📭 No tables loaded yet. Upload CSVs or connect to MySQL.")
else:
    for tbl_name, df in all_tables.items():
        with st.expander(f"📄 `{tbl_name}` ({len(df)} rows, {len(df.columns)} cols)"):
            if tbl_name in st.session_state.delimiters:
                st.caption(f"CSV Delimiter: `{st.session_state.delimiters[tbl_name]}`")
            
            st.dataframe(df.head(50), height=250)
            
            # Download
            st.download_button("⬇️ Download CSV", data=df.to_csv(index=False).encode("utf-8"), 
                               file_name=f"{tbl_name}.csv", mime="text/csv")
            
            # Table Description
            desc = st.text_area(f"📝 Table Description: `{tbl_name}`", 
                                value=st.session_state.table_descriptions.get(tbl_name, ""), 
                                key=f"tbl_desc_{tbl_name}")
            st.session_state.table_descriptions[tbl_name] = desc
            
            # Column Descriptions
            st.markdown("**🔍 Column Descriptions**")
            cols = st.columns(3)
            for i, col in enumerate(df.columns):
                with cols[i % 3]:
                    c_desc = st.text_input(f"`{col}`", 
                                           value=st.session_state.column_descriptions.get(tbl_name, {}).get(col, ""), 
                                           key=f"col_{tbl_name}_{col}")
                    st.session_state.column_descriptions.setdefault(tbl_name, {})[col] = c_desc

st.markdown("---")

# ===============================#
# 🔍 4. Natural Language → SQL → DuckDB
# ===============================#
st.subheader("💬 Ask Questions in Natural Language")

# Check if API key is available
has_api_key = bool(st.session_state.get("openai_api_key", ""))

if not has_api_key:
    st.warning("⚠️ **API Key Required** - Please add your OpenAI API key in the sidebar to use Natural Language to SQL conversion.")
    st.info("💡 You can still use the **Custom SQL Query** section below to run SQL manually on your uploaded data.")

query_input = st.text_area(
    "🔍 Your Question:", 
    placeholder="e.g., Show all rows where age > 50 and group by department", 
    height=80,
    disabled=not has_api_key  # Disable if no API key
)

if query_input and has_api_key and st.button("🚀 Generate & Run SQL", type="primary"):
    with st.spinner("🔧 Building prompt & generating SQL..."):
        full_prompt = build_prompt(
            user_query=query_input,
            table_descriptions=st.session_state.table_descriptions,
            column_descriptions=st.session_state.column_descriptions,
            uploaded_dataframes=all_tables
        )
        
        with st.expander("📝 Prompt Sent to LLM"):
            st.code(full_prompt, language="text")
            
        try:
            sql_query = generate_sql_from_prompt(full_prompt, api_key=st.session_state["openai_api_key"])
            
            st.subheader("💡 Generated SQL:")
            st.code(sql_query, language="sql")
            
            st.info("💡 **Note:** DuckDB executes the query. MySQL-specific syntax may need standard SQL equivalents.")
            
            try:
                con = duckdb.connect()
                for t_name, t_df in all_tables.items():
                    con.register(t_name, t_df)
                    
                result_df = con.execute(sql_query).df()
                con.close()
                
                st.success("✅ Query executed successfully!")
                st.dataframe(result_df, height=400)
                
                st.download_button("⬇️ Download Result", data=result_df.to_csv(index=False).encode("utf-8"), 
                                   file_name="query_result.csv", mime="text/csv")
            except Exception as e:
                st.error(f"❌ **Execution Error:** `{e}`\n💡 Check SQL syntax or ensure table/column names match exactly.")
                
        except Exception as e:
            st.error(f"❌ **SQL Generation Error:** `{e}`")

# ===============================#
# 🧮 5. Manual SQL Runner (Always Available)
# ===============================#
st.subheader("🧮 Run Custom SQL Queries")
st.caption("💡 This works even without an API key - run SQL directly on your uploaded data")

custom_sql = st.text_area("✍️ Enter SQL:", height=100, placeholder="SELECT * FROM your_table WHERE condition")

if st.button("▶️ Run Custom Query"):
    if not custom_sql.strip():
        st.warning("⚠️ Please enter a SQL query.")
    elif not all_tables:
        st.warning("⚠️ Please upload CSV files or load MySQL tables first.")
    else:
        try:
            con = duckdb.connect()
            for t_name, t_df in all_tables.items():
                con.register(t_name, t_df)
                
            result_df = con.execute(custom_sql).df()
            con.close()
            
            st.success("✅ Query executed!")
            st.dataframe(result_df, height=400)
            
            st.download_button("⬇️ Download Result", data=result_df.to_csv(index=False).encode("utf-8"), 
                               file_name="manual_result.csv", mime="text/csv")
        except Exception as e:
            st.error(f"❌ **Execution Error:** `{e}`")