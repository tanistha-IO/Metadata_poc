import os
from databricks.sdk import WorkspaceClient
from helper_metadata import (
    get_databricks_connection,
    fetch_table_data,
    get_table_metadata,
    prepare_prompt,
    call_groq_api,
    update_json_file
)

def generate_downstream_metadata():
    """Main orchestration function for metadata generation."""
    databricks_host = os.getenv("DATABRICKS_HOST")
    databricks_token = os.getenv("DATABRICKS_TOKEN")

    if not databricks_host or not databricks_token:
        raise ValueError("Databricks credentials not found in environment variables")

    w = WorkspaceClient(host=databricks_host, token=databricks_token)

    upstream_table_names = [
        "my_catalog.upstream.customers",
        "my_catalog.upstream.orders"
    ]
    downstream_table_name = "my_catalog.downstream.customer_order_summary"
    all_tables = upstream_table_names + [downstream_table_name]

    connection = get_databricks_connection()
    table_data_map = fetch_table_data(connection, all_tables)

    upstream_tables = [get_table_metadata(w, t) for t in upstream_table_names]
    downstream_table = get_table_metadata(w, downstream_table_name)

    sql_file_path = "/home/user/project -1/transformation_query.sql"
    with open(sql_file_path, "r") as sql_file:
        sql_query = sql_file.read().strip()
    print("\nSQL query read successfully:\n", sql_query)

    prompt_data = prepare_prompt(upstream_tables, downstream_table, sql_query, table_data_map)
    ai_json = call_groq_api(prompt_data, downstream_table["name"])
    update_json_file("downstream_metadata.json", ai_json)

    print("\n--- PROCESS COMPLETED SUCCESSFULLY ---")

if __name__ == "__main__":
    generate_downstream_metadata()
