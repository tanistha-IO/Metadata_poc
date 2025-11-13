import os
import json
import datetime
from decimal import Decimal
from databricks import sql
from databricks.sdk import WorkspaceClient
import groq
from git import Repo
from github import Github, Auth


def get_databricks_connection():
    return sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN"),
        user_agent_entry="metadata_pipeline"
    )


def fetch_table_data(connection, tables):
    from datetime import date, datetime as dt
    table_data_map = {}
    print("\nFetching sample data from tables...")
    with connection.cursor() as cursor:
        for table in tables:
            print(f"\n--- Table: {table} ---")
            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            formatted_rows = []
            for r in rows:
                row_data = dict(zip(columns, r))
                for k, v in row_data.items():
                    if isinstance(v, (date, dt)):
                        row_data[k] = v.isoformat()
                    elif isinstance(v, Decimal):
                        row_data[k] = float(v)
                formatted_rows.append(row_data)
            table_data_map[table] = formatted_rows
    return table_data_map


def get_table_metadata(w, table_name):
    catalog, schema, table = table_name.split(".")
    table_info = w.tables.get(f"{catalog}.{schema}.{table}")
    columns = [
        {
            "name": c.name,
            "type": c.type_text,
            "description": c.comment or "No description available"
        }
        for c in table_info.columns
    ]
    return {
        "catalog": catalog,
        "schema": schema,
        "name": table,
        "comment": table_info.comment or f"No description available for table '{table}'",
        "columns": columns
    }


def prepare_prompt(upstream_tables, downstream_table, sql_query, table_data_map):
    return {
        "prompt": (
            "Based on the following upstream tables, SQL transformation, and sample data, "
            "generate a JSON response with:\n"
            '1. "description" (detailed description of downstream table without mentioning upstream tables)\n'
            f"UPSTREAM TABLES:\n{json.dumps(upstream_tables, indent=2)}\n"
            f"SAMPLE DATA:\n{json.dumps(table_data_map, indent=2)}\n"
            f"SQL TRANSFORMATION:\n{sql_query}\n"
            f"DOWNSTREAM TABLE:\n{json.dumps(downstream_table, indent=2)}"
        )
    }


def call_groq_api(prompt_data, downstream_table_name):
    api_key = os.getenv("GROQ_API_KEY")
    client = groq.Client(api_key=api_key)
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "You are a data engineer. Respond only with valid JSON."},
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
    return ai_json


def update_json_file(file_path, ai_json):
    with open(file_path, "r") as f:
        existing_data = json.load(f)
        if not isinstance(existing_data, list):
            existing_data = [existing_data]

    existing_data.append(ai_json)
    with open(file_path, "w") as f:
        json.dump(existing_data, f, indent=2)
    print(f"\n Updated '{file_path}' successfully!")
    return file_path


def generate_metadata():
    databricks_host = os.getenv("DATABRICKS_HOST")
    databricks_token = os.getenv("DATABRICKS_TOKEN")
    w = WorkspaceClient(host=databricks_host, token=databricks_token)

    upstream = ["my_catalog.upstream.customers", "my_catalog.upstream.orders"]
    downstream = "my_catalog.downstream.customer_order_summary"

    connection = get_databricks_connection()
    table_data_map = fetch_table_data(connection, upstream + [downstream])

    upstream_meta = [get_table_metadata(w, t) for t in upstream]
    downstream_meta = get_table_metadata(w, downstream)

    sql_path = "/home/user/project-1/transformation_query.sql"
    with open(sql_path, "r") as f:
        sql_query = f.read().strip()

    prompt_data = prepare_prompt(upstream_meta, downstream_meta, sql_query, table_data_map)
    ai_json = call_groq_api(prompt_data, downstream_meta["name"])
    return update_json_file("downstream_metadata.json", ai_json)



def create_branch_commit_push_pr(file_path):
    repo_path = "/home/user/project-1"
    repo = Repo(repo_path)
    github_repo = "tanistha-IO/Metadata_poc"
    token = os.getenv("GITHUB_TOKEN")

    gh = Github(auth=Auth.Token(token))
    g_repo = gh.get_repo(github_repo)

    branch_name = f"auto-update-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    base_branch = "main"

    repo.git.checkout("-b", branch_name)
    print(f" Created and switched to branch: {branch_name}")

    repo.git.add(file_path)
    repo.index.commit(f"Automated metadata update {datetime.datetime.now().isoformat()}")

    origin = repo.remote(name="origin")
    origin.push(refspec=f"{branch_name}:{branch_name}", set_upstream=True)
    print(f" Pushed branch '{branch_name}' to remote.")

    open_prs = g_repo.get_pulls(state="open", base=base_branch)
    existing = [pr for pr in open_prs if pr.head.ref == branch_name]
    if existing:
        print(f"🔗 Existing PR found: {existing[0].html_url}")
    else:
        new_pr = g_repo.create_pull(
            title=f"Automated PR from {branch_name}",
            body="This PR contains automatically generated downstream metadata updates.",
            head=branch_name,
            base=base_branch,
        )
        print(f"Created new PR: {new_pr.html_url}")
