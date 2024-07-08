
from boto3 import client
import pandas as pd
from botocore.exceptions import NoCredentialsError
from fastapi import File, HTTPException
import csv
from io import StringIO
from .validations import Validations


class ReadWriteOps:
    def __init__(self, s3_client: client):
        self.config = config
        self.s3_client =s3_client

    def upload_to_s3(self, file: File, object_name: str =None):
        if object_name is None:
            object_name = file.filename

        try:
            self.s3_client.upload_fileobj(file.file, self.config.S3_BUCKET_NAME, object_name)
        except NoCredentialsError:
            raise HTTPException(status_code=403, detail="Credentials not available")
        
    def download_from_s3(self, object_name: str, file: File):
        try:
            self.s3_client.download_file(self.config.S3_BUCKET_NAME, object_name, file)
            df = pd.read_csv(file)
            return df
        except NoCredentialsError:
            raise HTTPException(status_code=403, detail="Credentials not available")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
    async def read_stream_chunks(self, upload_file: File) -> pd.DataFrame:
        
        # Limitar el tamaño máximo de las primeras 100 filas
        max_rows = self.config.ROWS_LIMIT
        rows = []
        reader = None

        # Definir el tamaño del chunk (por ejemplo, 1024 bytes)
        chunk_size = self.config.STREAM_FILE_CHUNKS_SIZE_KB
        
        # Procesar el archivo en partes mientras se sube
        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break

            if reader is None:
                # Inicializar el lector CSV en el primer chunk
                reader = csv.reader(StringIO(chunk.decode('utf-8')))
            else:
                # Continuar leyendo del archivo
                reader = csv.reader(StringIO(chunk.decode('utf-8')), reader.dialect)
            
            for row in reader:
                rows.append(row)
                Validations.max_rows_count(rows,self.config.ROWS_LIMIT)

            if len(rows) >= max_rows:
                break

        # Convertir las filas a un DataFrame de pandas
        df = pd.DataFrame(rows[:max_rows])
        
        return df
        
