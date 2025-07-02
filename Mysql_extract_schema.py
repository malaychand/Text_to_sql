# extract_schema.py
import mysql.connector

# Helper to decode bytes
def decode_if_bytes(val):
    return val.decode('utf-8') if isinstance(val, bytes) else val

def get_mysql_schema(host, user, passwd):
    conn = mysql.connector.connect(host=host, user=user, passwd=passwd)
    cursor = conn.cursor()
    cursor.execute("SHOW DATABASES")
    all_databases = [db[0] for db in cursor]

    excluded_dbs = {"information_schema", "performance_schema", "mysql", "sys"}
    full_schema_info = {}

    for db_name in all_databases:
        if db_name in excluded_dbs:
            continue

        try:
            db_conn = mysql.connector.connect(
                host=host,
                user=user,
                passwd=passwd,
                database=db_name
            )
            db_cursor = db_conn.cursor()
            db_cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
            tables = db_cursor.fetchall()
            if not tables:
                continue

            db_structure = {
                "tables": {},
                "views": {},
                "functions": {},
                "production_call": {}
            }

            for table in tables:
                table_name = decode_if_bytes(table[0])
                query = f"""
                    SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_KEY, EXTRA 
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = '{db_name}' AND TABLE_NAME = '{table_name}'
                """
                db_cursor.execute(query)
                columns = db_cursor.fetchall()

                schema_info = {}
                for col in columns:
                    col_name = decode_if_bytes(col[0])
                    col_type = decode_if_bytes(col[1])
                    col_key = decode_if_bytes(col[2])
                    extra = decode_if_bytes(col[3])

                    column_schema = col_type
                    if col_key == "PRI":
                        column_schema += " PRIMARY KEY"
                    if "auto_increment" in extra:
                        column_schema += " AUTO_INCREMENT"

                    schema_info[col_name] = column_schema

                db_structure["tables"][table_name] = {
                    "schema_info": schema_info,
                    "info": f"Provide description for table '{table_name}'."
                }

            if db_structure["tables"]:
                full_schema_info[db_name] = db_structure

            db_conn.close()

        except Exception as e:
            print(f"⚠️ Error processing {db_name}: {e}")
            continue

    return full_schema_info
