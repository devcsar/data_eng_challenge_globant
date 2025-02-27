from boto3 import client
import pandas as pd
from api.models import HiredEmployees
from botocore.exceptions import NoCredentialsError
from fastapi import File, HTTPException
import csv
from io import StringIO
from .validations import Validations
from dateutil.parser import parse as parse_datetime
from cassandra.cluster import Session


class ReadWriteOps:
    def __init__(self, config, s3_client: client):
        self.config = config
        self.s3_client = s3_client

    def upload_to_s3(self, file: File, object_name: str = None):
        if object_name is None:
            object_name = file.filename

        try:
            self.s3_client.upload_fileobj(
                file.file, self.config.S3_BUCKET_NAME, object_name
            )
        except NoCredentialsError:
            raise HTTPException(
                status_code=403, detail="Credentials not available"
            )

    def download_from_s3(self, object_name: str, file: File):
        try:
            self.s3_client.download_file(
                self.config.S3_BUCKET_NAME, object_name, file
            )
            df = pd.read_csv(file)
            return df
        except NoCredentialsError:
            raise HTTPException(
                status_code=403, detail="Credentials not available"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def read_stream_chunks(
        self, upload_file: File, rows_limit: int, chunk_size: int
    ) -> tuple[bool, list]:
        """
        Process file in chunks while is uploading
        """

        rows = []
        reader = None

        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break

            if reader is None:
                # Inicializar el lector CSV en el primer chunk
                reader = csv.reader(StringIO(chunk.decode("utf-8")))
            else:
                # Continuar leyendo del archivo
                reader = csv.reader(
                    StringIO(chunk.decode("utf-8")), reader.dialect
                )

            for row in reader:
                rows.append(row)
                if not Validations.max_rows_count(
                    rows, self.config.ROWS_LIMIT
                ):
                    return (False, rows)

            if len(rows) >= rows_limit:
                break

        # Convertir las filas a un DataFrame de pandas
        # df = pd.DataFrame(rows[:rows_limit])

        return (True, rows)

    def write_rows_db(
        self, session: Session, data: pd.DataFrame
    ) -> tuple[bool, pd.DataFrame]:
        hired_employee_model = HiredEmployees(session)

        for _, row in data.iterrows():
            hired_employee_model.create(
                id=int(row["id"]),
                name=row["name"],
                datetime=parse_datetime(row["datetime"]),
                department_id=int(row["department_id"]),
                job_id=int((row["job_id"])),
            )
        return ("File successfully processed and data uploaded", data)
