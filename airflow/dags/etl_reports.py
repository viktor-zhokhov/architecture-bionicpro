from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from clickhouse_driver import Client as ClickHouseClient


CLICKHOUSE_HOST = "clickhouse"
CLICKHOUSE_PORT = 9000
POSTGRES_CONN_ID = "crm_postgres"

default_args = {
    "owner": "bionicpro",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def extract_crm_customers(**context):
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    records = hook.get_records(
        """
        SELECT id, first_name, last_name, email, phone, created_at
        FROM customers
        WHERE updated_at >= %(since)s
        """,
        parameters={"since": context["data_interval_start"]},
    )
    context["ti"].xcom_push(key="customers", value=records)


def extract_telemetry(**context):
    hook = PostgresHook(postgres_conn_id="telemetry_postgres")
    records = hook.get_records(
        """
        SELECT
            id, customer_id, device_id,
            signal_quality, battery_level, response_time_ms,
            session_duration_sec, movements_count,
            recorded_at
        FROM telemetry
        WHERE recorded_at >= %(since)s
        """,
        parameters={"since": context["data_interval_start"]},
    )
    context["ti"].xcom_push(key="telemetry", value=records)


def load_customers_to_clickhouse(**context):
    ch = ClickHouseClient(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT)
    ch.execute("CREATE DATABASE IF NOT EXISTS bionicpro")
    ch.execute(
        """
        CREATE TABLE IF NOT EXISTS bionicpro.customers (
            id          UInt64,
            first_name  String,
            last_name   String,
            email       String,
            phone       String,
            created_at  DateTime
        ) ENGINE = ReplacingMergeTree()
        ORDER BY id
        """
    )

    rows = context["ti"].xcom_pull(key="customers", task_ids="extract_crm_customers")
    if not rows:
        return
    ch.execute(
        "INSERT INTO bionicpro.customers VALUES",
        rows,
    )


def load_telemetry_to_clickhouse(**context):
    ch = ClickHouseClient(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT)
    ch.execute("CREATE DATABASE IF NOT EXISTS bionicpro")
    ch.execute(
        """
        CREATE TABLE IF NOT EXISTS bionicpro.telemetry (
            id                   UInt64,
            customer_id          UInt64,
            device_id            String,
            signal_quality       Float32,
            battery_level        Float32,
            response_time_ms     Float32,
            session_duration_sec UInt32,
            movements_count      UInt32,
            recorded_at          DateTime
        ) ENGINE = MergeTree()
        ORDER BY (customer_id, recorded_at)
        """
    )

    rows = context["ti"].xcom_pull(key="telemetry", task_ids="extract_telemetry")
    if not rows:
        return
    ch.execute(
        "INSERT INTO bionicpro.telemetry VALUES",
        rows,
    )


def build_report_mart(**context):
    ch = ClickHouseClient(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT)
    ch.execute(
        """
        CREATE TABLE IF NOT EXISTS bionicpro.report_mart (
            customer_id          UInt64,
            first_name           String,
            last_name            String,
            email                String,
            device_id            String,
            total_sessions       UInt64,
            total_movements      UInt64,
            avg_response_time_ms Float64,
            avg_signal_quality   Float64,
            avg_battery_level    Float64,
            last_activity        DateTime,
            report_date          Date
        ) ENGINE = ReplacingMergeTree(report_date)
        ORDER BY (customer_id, device_id)
        """
    )

    report_date = context["data_interval_end"].strftime("%Y-%m-%d")
    ch.execute(
        f"""
        INSERT INTO bionicpro.report_mart
        SELECT
            t.customer_id,
            c.first_name,
            c.last_name,
            c.email,
            t.device_id,
            count()              AS total_sessions,
            sum(t.movements_count) AS total_movements,
            avg(t.response_time_ms) AS avg_response_time_ms,
            avg(t.signal_quality)   AS avg_signal_quality,
            avg(t.battery_level)    AS avg_battery_level,
            max(t.recorded_at)      AS last_activity,
            toDate('{report_date}') AS report_date
        FROM bionicpro.telemetry t
        JOIN bionicpro.customers c ON t.customer_id = c.id
        GROUP BY t.customer_id, c.first_name, c.last_name, c.email, t.device_id
        """
    )


with DAG(
    dag_id="bionicpro_etl_reports",
    default_args=default_args,
    description="ETL: CRM + телеметрия -> ClickHouse -> витрина отчётности",
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["bionicpro", "etl", "reports"],
) as dag:

    t_extract_crm = PythonOperator(
        task_id="extract_crm_customers",
        python_callable=extract_crm_customers,
    )

    t_extract_telemetry = PythonOperator(
        task_id="extract_telemetry",
        python_callable=extract_telemetry,
    )

    t_load_customers = PythonOperator(
        task_id="load_customers_to_clickhouse",
        python_callable=load_customers_to_clickhouse,
    )

    t_load_telemetry = PythonOperator(
        task_id="load_telemetry_to_clickhouse",
        python_callable=load_telemetry_to_clickhouse,
    )

    t_build_mart = PythonOperator(
        task_id="build_report_mart",
        python_callable=build_report_mart,
    )

    t_extract_crm >> t_load_customers >> t_build_mart
    t_extract_telemetry >> t_load_telemetry >> t_build_mart
