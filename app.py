import duckdb
import streamlit as st
import pandas as pd
import mysql.connector
from Mysql_extract_schema import get_mysql_schema
from csv_utils import detect_encoding, detect_delimiter  
from prompt_builder import build_prompt
from llm_to_sql import generate_sql_from_prompt

st.set_page_config(page_title="📊 Unified CSV & MySQL Viewer", layout="wide")
st.title("🔗 CSV & MySQL Table Annotator")

# Session state initialization
for key in ["uploaded_data", "file_prompts", "column_descriptions", "dataframes", "table_descriptions", "delimiters"]:
    if key not in st.session_state:
        st.session_state[key] = {}

# ===============================#
# 📤 1. CSV Upload & Annotation
# ===============================#
st.header("📁 Upload CSV Files")
with st.form(key="csv_upload_form"):
    uploaded_files = st.file_uploader("Upload CSV files", type="csv", accept_multiple_files=True)
    submit = st.form_submit_button("📤 Upload These Files")

if submit and uploaded_files:
    for file in uploaded_files:
        file_name = file.name.replace(".csv", "")
        if file_name not in st.session_state.uploaded_data:
            try:
                # ✅ Detect encoding and delimiter
                encoding = detect_encoding(file)
                delimiter = detect_delimiter(file, encoding)
                
                # ✅ Load DataFrame using detected settings
                df = pd.read_csv(file, delimiter=delimiter, encoding=encoding)

                # ✅ Store data and delimiter
                st.session_state.uploaded_data[file_name] = df
                st.session_state.delimiters[file_name] = delimiter

                st.success(f"✅ Uploaded: {file.name} (Delimiter: '{delimiter}')")
            except Exception as e:
                st.error(f"❌ Error loading {file.name}: {e}")
        else:
            st.warning(f"⚠️ File '{file.name}' already uploaded. Skipping.")

# ===============================#
# 🔌 2. MySQL Table Connector
# ===============================#
st.header("🧩 Connect to MySQL Database")

with st.expander("Enter MySQL Credentials"):
    host = st.text_input("Host", value="localhost")
    user = st.text_input("Username", value="root")
    password = st.text_input("Password", type="password")

if st.button("Connect and Fetch Schema"):
    with st.spinner("🔄 Connecting..."):
        try:
            schema_data = get_mysql_schema(host, user, password)
            st.success("✅ Fetched schema successfully!")
            st.session_state["schema_info"] = schema_data
            #st.write(st.session_state)
        except Exception as e:
            st.error(f"❌ Failed: {e}")

if "schema_info" in st.session_state:
    schema_data = st.session_state["schema_info"]
    st.subheader("📂 Select MySQL Tables")

    selected_dbs = st.multiselect("Select Databases", list(schema_data.keys()))
    for db in selected_dbs:
        st.markdown(f"### 🗂️ `{db}`")
        tables = list(schema_data[db]["tables"].keys())
        selected_tables = st.multiselect(f"Select Tables from `{db}`", tables, key=f"{db}_tables")

        if selected_tables:
            if st.button(f"📥 Load from `{db}`", key=f"upload_{db}"):
                try:
                    conn = mysql.connector.connect(host=host, user=user, passwd=password, database=db)
                    cursor = conn.cursor()

                    for table in selected_tables:
                        cursor.execute(f"SELECT * FROM {table}")
                        rows = cursor.fetchall()
                        columns = [i[0] for i in cursor.description]
                        df = pd.DataFrame(rows, columns=columns)

                        st.session_state.dataframes[table] = df
                        st.session_state.table_descriptions.setdefault(table, schema_data[db]["tables"][table]["info"])

                    conn.close()
                    st.success(f"✅ Loaded tables from `{db}`")
                except Exception as e:
                    st.error(f"❌ Failed to load: {e}")

# ===============================#
# 🧾 3. Display + Annotation
# ===============================#
st.header("📊 Uploaded Tables")

# Combine CSV and MySQL tables
all_tables = {**st.session_state.uploaded_data, **st.session_state.dataframes}

if all_tables:
    for table_name, df in all_tables.items():
        with st.expander(f"📄 {table_name}"):
            # Show detected delimiter if available
            if table_name in st.session_state.delimiters:
                st.markdown(f"**Delimiter used:** `{st.session_state.delimiters[table_name]}`")

            st.dataframe(df)

            # Download button
            csv_download = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", data=csv_download, file_name=f"{table_name}.csv", mime="text/csv")

            # Table-level description
            default_table_desc = st.session_state.table_descriptions.get(table_name, st.session_state.file_prompts.get(table_name, ""))
            table_desc = st.text_area(f"📝 Describe `{table_name}` table:", value=default_table_desc, key=f"desc_{table_name}")
            st.session_state.table_descriptions[table_name] = table_desc

            # Column-level descriptions
            st.markdown("**🔍 Column Descriptions**")
            if table_name not in st.session_state.column_descriptions:
                st.session_state.column_descriptions[table_name] = {}

            for col in df.columns:
                default_col_desc = st.session_state.column_descriptions[table_name].get(col, "")
                col_desc = st.text_input(f"• {col}:", value=default_col_desc, key=f"{table_name}_{col}_desc")
                st.session_state.column_descriptions[table_name][col] = col_desc
st.markdown("---")
st.markdown(" ")


# ===============================#
# 🔍 4. Natural Language → SQL → DuckDB Execution
# ===============================#
st.header("🧠 Ask Questions in Natural Language")

query_input = st.text_input("🔍 Your Question:", placeholder="e.g., Show all rows where age > 50")

if query_input:
    with st.spinner("🔧 Generating SQL query..."):
        # Build full prompt using table metadata and user's query
        full_prompt = build_prompt(
            user_query=query_input,
            table_descriptions=st.session_state.table_descriptions,
            column_descriptions=st.session_state.column_descriptions,
            uploaded_dataframes=all_tables
        )
        
        # ✅ Show the generated prompt
        st.subheader("📝 Prompt Sent to LLM:")
        with st.expander("📝 Click to view Prompt Sent to LLM"):
            st.code(full_prompt)

        # ✅ Generate SQL
        sql_query = generate_sql_from_prompt(full_prompt)

        # ✅ Show the generated SQL
        st.subheader("💡 Generated SQL:")
        st.code(sql_query, language="sql")

        try:
            # ✅ Register all tables (MySQL or CSV) with DuckDB
            con = duckdb.connect()
            for table_name, df in all_tables.items():
                con.register(table_name, df)

            # ✅ Execute generated SQL
            result_df = con.execute(sql_query).df()

            # ✅ Show results
            st.success("✅ SQL executed successfully!")
            st.dataframe(result_df)

            # ✅ Optionally allow result download
            csv_result = result_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Result as CSV", data=csv_result, file_name="query_result.csv", mime="text/csv")

        except Exception as e:
            st.error(f"❌ SQL Execution Error: {e}")


# ===============================#
# 🧮 5. Run Custom SQL Queries (Manual)
# ===============================#
st.header("🧮 Run Custom SQL Queries")

custom_sql = st.text_area("✍️ Enter your SQL query below:", height=100, placeholder="e.g., SELECT * FROM your_table WHERE age > 30")

if st.button("▶️ Run SQL Query"):
    try:
        # ✅ Connect to DuckDB
        con = duckdb.connect()

        # ✅ Register all dataframes to DuckDB
        for table_name, df in all_tables.items():
            con.register(table_name, df)

        # ✅ Execute the user's SQL query
        result_df = con.execute(custom_sql).df()

        # ✅ Show the result
        st.success("✅ Query executed successfully!")
        st.dataframe(result_df)

        # ✅ Allow downloading results
        csv_result = result_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Result as CSV", data=csv_result, file_name="manual_query_result.csv", mime="text/csv")

    except Exception as e:
        st.error(f"❌ SQL Execution Error: {e}")
