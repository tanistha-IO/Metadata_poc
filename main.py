import groq
import os
import json
import datetime
from decimal import Decimal
from databricks.sdk import WorkspaceClient
from databricks import sql
from dotenv import load_dotenv

load_dotenv()

def get_databricks_connection():
    return sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN"),
        user_agent_entry="product_name"
    )

def fetch_table_data(connection, tables):
    table_data_map = {}
    print("\nFetching sample data from tables...")

    with connection.cursor() as cursor:
        for table in tables:
            print(f"\n--- Table: {table} ---")
            try:
                cursor.execute(f"SELECT * FROM {table} LIMIT 3")
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

                formatted_rows = []
                for r in rows:
                    row_data = dict(zip(columns, r))
                    for k, v in row_data.items():
                        if isinstance(v, (datetime.date, datetime.datetime)):
                            row_data[k] = v.isoformat()
                        elif isinstance(v, Decimal):
                            row_data[k] = float(v)
                    formatted_rows.append(row_data)

                table_data_map[table] = formatted_rows
                for r in formatted_rows:
                    print(json.dumps(r, indent=2))

            except Exception as e:
                print(f" Error reading table {table}: {e}")
                table_data_map[table] = []
    return table_data_map

def get_table_metadata(w, table_name):
    catalog, schema, table = table_name.split(".")
    table_info = w.tables.get(f"{catalog}.{schema}.{table}")
    databricks_host = os.getenv("DATABRICKS_HOST")
    databricks_token = os.getenv("DATABRICKS_TOKEN")
    w = WorkspaceClient(host=databricks_host, token=databricks_token)
    columns = []
    for c in table_info.columns:
        col_description = c.comment or "No description available"
        columns.append({
            "name": c.name,
            "type": c.type_text,
            "description": col_description
        })

    print(f"\nColumns for table '{table_name}':")
    for col in columns:
        print(f"{col['name']} ({col['type']}): {col['description']}")

    table_comment = table_info.comment or f"No description available for table '{table}'"
    return {
        "catalog": catalog,
        "schema": schema,
        "name": table,
        "comment": table_comment,
        "columns": columns
    }

def prepare_prompt(upstream_tables, downstream_table, sql_query, table_data_map):
    return {
        "prompt": (
            "Based on the following upstream tables, SQL transformation, and sample data, "
            "generate a JSON response with:\n"
            '1. \"description (detailed description of downstream table and do not mention upstream table names)\"\n'
            f"UPSTREAM TABLES:\n{json.dumps(upstream_tables, indent=2)}\n"
            f"SAMPLE DATA:\n{json.dumps(table_data_map, indent=2)}\n"
            f"SQL TRANSFORMATION:\n{sql_query}\n"
            f"DOWNSTREAM TABLE:\n{json.dumps(downstream_table, indent=2)}"
        )
    }

def call_groq_api(prompt_data, downstream_table_name):
    api_key = "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"
    client = groq.Client(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are a data engineer thinking from a business perspective. Respond only with valid JSON."},
                {"role": "user", "content": json.dumps(prompt_data)}
            ]
        )

        ai_text = response.choices[0].message.content.strip()
        if ai_text.startswith('"') and ai_text.endswith('"'):
            ai_text = ai_text[1:-1].replace('\\"', '"')

        try:
            ai_json = json.loads(ai_text)
            ai_json["table"] = downstream_table_name
        except json.JSONDecodeError:
            ai_json = {"table": downstream_table_name, "description": ai_text}

    except Exception as e:
        ai_json = {"table": downstream_table_name, "description": str(e)}

    return ai_json

def update_json_file(file_path, ai_json):
    try:
        with open(file_path, "r") as f:
            existing_data = json.load(f)
            if not isinstance(existing_data, list):
                existing_data = [existing_data]
    except (FileNotFoundError, json.JSONDecodeError):
        existing_data = [
            {"table": "t1", "description": "d1"},
            {"table": "t2", "description": "d2"}
        ]

    existing_data.append(ai_json)
    with open(file_path, "w") as f:
        json.dump(existing_data, f, indent=2)

    print(f"\nUpdated '{file_path}' successfully!")
    print(json.dumps(existing_data, indent=2))

def generate_downstream_metadata():
    databricks_host = os.getenv("DATABRICKS_HOST")
    databricks_token = os.getenv("DATABRICKS_TOKEN")

    if not databricks_host or not databricks_token:
        raise ValueError("Databricks credentials not found in environment variables")

    upstream_table_names = [
        "my_catalog.upstream.customers",
        "my_catalog.upstream.orders"
    ]
    downstream_table_name = "my_catalog.downstream.customer_order_summary"
    all_tables = upstream_table_names + [downstream_table_name]

    connection = get_databricks_connection()
    table_data_map = fetch_table_data(connection, all_tables)
    w = WorkspaceClient(host=databricks_host, token=databricks_token)
    upstream_tables = [get_table_metadata(w, t) for t in upstream_table_names]
    downstream_table = get_table_metadata(w, downstream_table_name)

    sql_file_path = "/home/user/project -1/transformation_query.sql"
    with open(sql_file_path, "r") as sql_file:
        sql_query = sql_file.read().strip()

    prompt_data = prepare_prompt(upstream_tables, downstream_table, sql_query, table_data_map)
    ai_json = call_groq_api(prompt_data, downstream_table["name"])
    update_json_file("downstream_metadata.json", ai_json)

if __name__ == "__main__":
    generate_downstream_metadata()
