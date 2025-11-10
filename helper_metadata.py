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
    """Establish a connection to Databricks SQL warehouse."""
    return sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN"),
        user_agent_entry="product_name"
    )

def fetch_table_data(connection, tables):
    """Fetch and format sample data from given tables."""
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
    """Retrieve table schema, catalog, and comments from Databricks."""
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
    metadata = {
        "catalog": catalog,
        "schema": schema,
        "name": table,
        "comment": table_comment,
        "columns": columns
    }

    print(f"\nMetadata for table '{table_name}':")
    print(json.dumps(metadata, indent=2))
    return metadata

def prepare_prompt(upstream_tables, downstream_table, sql_query, table_data_map):
    """Prepare the AI prompt using table metadata, SQL query, and sample data."""
    prompt = {
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

    print("\nPrompt data prepared:")
    print(json.dumps(prompt, indent=2))
    return prompt

def call_groq_api(prompt_data, downstream_table_name):
    """Call Groq API to generate table description."""
    api_key = os.getenv("GROQ_API_KEY")  # safer
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

    print("\nAI JSON response:")
    print(json.dumps(ai_json, indent=2))
    return ai_json

def update_json_file(file_path, ai_json):
    """Append AI-generated metadata to downstream JSON file."""
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
