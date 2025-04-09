import streamlit as st
import pandas as pd
import duckdb
from help import convert_to_sql  # Helper that converts NL -> SQL

st.set_page_config(page_title="Chat with CSV", layout="centered")
st.title("💬 Chat with Your CSV Data")

# Upload section
uploaded_file = st.file_uploader("📁 Upload your CSV file", type=["csv"])

# Session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "df" not in st.session_state:
    st.session_state.df = None
if "table_schema" not in st.session_state:
    st.session_state.table_schema = None
if "conn" not in st.session_state:
    st.session_state.conn = None

# After file upload
if uploaded_file is not None and st.session_state.df is None:
    try:
        df = pd.read_csv(uploaded_file, sep=';', engine='python')
        st.session_state.df = df

        # Register dataframe in DuckDB
        conn = duckdb.connect(database=":memory:")
        conn.register("df", df)
        st.session_state.conn = conn

        # Extract schema
        schema = ", ".join([f"{col} {str(dtype)}" for col, dtype in df.dtypes.items()])
        st.session_state.table_schema = schema

        st.success("✅ File uploaded and ready to chat!")

    except Exception as e:
        st.error(f"❌ Failed to load file: {e}")

# If data is loaded
if st.session_state.df is not None:
    st.subheader("👁️ Preview of Your Data")
    st.dataframe(st.session_state.df.head(2))

    st.text_area("📋 Table Schema:", value=st.session_state.table_schema, height=100)

    st.subheader("💬 Ask questions about your data")

    # Input for new question
    user_question = st.chat_input("Type your question:")

    if user_question:
        st.session_state.chat_history.append({"role": "user", "content": user_question})

        try:
            with st.spinner("🔍 Translating to SQL..."):
                # Convert first 2 rows to markdown format
                df_head = st.session_state.df.head(2).to_markdown(index=False)
                sql_query = convert_to_sql(user_question, st.session_state.table_schema, df_head)

            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"**Generated SQL:**\n```sql\n{sql_query}\n```"
            })

            result = st.session_state.conn.execute(sql_query).fetchdf()
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "**Query Result:**",
                "data": result
            })

        except Exception as e:
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"❌ Error: {e}"
            })

    # Show full chat after processing input
    for message in st.session_state.chat_history:
        with st.chat_message("user" if message["role"] == "user" else "assistant"):
            st.markdown(message["content"])
            if "data" in message:
                st.dataframe(message["data"])

else:
    st.info("📤 Please upload a CSV file to start chatting.")
