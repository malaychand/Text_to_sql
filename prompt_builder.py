# # prompt_builder.py

# def build_prompt(user_query, table_descriptions, column_descriptions, delimiters, uploaded_dataframes):
#     lines = ["You are an AI that converts natural language into accurate SQL queries.\n",
#              "## Table Metadata:\n"]

#     for table_name, df in uploaded_dataframes.items():
#         desc = table_descriptions.get(table_name, "No description")
#         delimiter = delimiters.get(table_name, ",")
#         lines.append(f"### Table: {table_name}")
#         lines.append(f"Description: {desc}")
#         lines.append(f"Delimiter: '{delimiter}'")

#         lines.append("Columns:")
#         for col, col_desc in column_descriptions.get(table_name, {}).items():
#             lines.append(f"- {col}: {col_desc}")

#         lines.append("\nSample Rows (first 2):")
#         lines.append(df.head(2).to_string(index=False))
#         lines.append("")

#     lines.append("## Instruction:")
#     lines.append("Based on the above table schema and sample rows, convert the following question to a valid SQL query.")
#     lines.append(f"Natural Language Query: \"{user_query}\"")
#     lines.append("\nAlways output a valid SQL query only, without explanation.\n")
#     return "\n".join(lines)


def build_prompt(user_query, table_descriptions, column_descriptions, uploaded_dataframes):
    lines = [
        "You are an AI that converts natural language into SQL queries.\n",
        "## Table Metadata:\n"
    ]

    for table_name, df in uploaded_dataframes.items():
        desc = table_descriptions.get(table_name, "No description provided.")
        lines.append(f"### Table: {table_name}")
        lines.append(f"Description: {desc}\n")

        lines.append("Columns:")
        for col in df.columns:
            col_desc = column_descriptions.get(table_name, {}).get(col, "No description")
            lines.append(f"- {col}: {col_desc}")

        lines.append("\nSample Rows (first 2):")
        lines.append(df.head(2).to_string(index=False))
        lines.append("")

    lines.extend([
        "\n## Instruction:",
        f"Translate the following query into valid SQL:\n\"{user_query}\"",
        "Only output the SQL query, nothing else.\n"
    ])

    return "\n".join(lines)
