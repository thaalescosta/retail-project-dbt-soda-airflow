from airflow.decorators import dag
from airflow.providers.google.cloud.transfers.local_to_gcs import LocalFilesystemToGCSOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateEmptyDatasetOperator
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator

from datetime import datetime, timedelta

@dag(
    start_date=datetime(2026,1,1),
    schedule=None,
    catchup=False,
    tags = ['retail'],
    default_args={
        'retries': 2,
        'retry_delay': timedelta(minutes=1),
    },
)
def retail():

    upload_csv_to_gcs = LocalFilesystemToGCSOperator(
        task_id="upload_csv_to_gcs",
        src='/usr/local/airflow/include/dataset/online_retail.csv',
        dst='raw/online_retail.csv',
        bucket='retail-project-dbt',
        gcp_conn_id='gcp',
        mime_type='text/csv'
    )

    create_retail_dataset = BigQueryCreateEmptyDatasetOperator(
        task_id='create_retail_dataset',
        dataset_id='retail',
        project_id='retail-dbt-airflow',
        gcp_conn_id='gcp',
        if_exists='ignore',
    )

    gcs_to_raw = GCSToBigQueryOperator(
        task_id='gcs_to_raw',
        bucket='retail-project-dbt',
        source_objects=['raw/online_retail.csv'],
        destination_project_dataset_table='retail-dbt-airflow.retail.raw_invoices',
        source_format='CSV',
        autodetect=True,
        create_disposition='CREATE_IF_NEEDED',
        write_disposition='WRITE_TRUNCATE',
        gcp_conn_id='gcp',
    )

    upload_csv_to_gcs >> create_retail_dataset >> gcs_to_raw

retail()