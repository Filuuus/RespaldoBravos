import boto3
from botocore.exceptions import NoCredentialsError
from app.config import Config

class S3Client:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=Config.S3_ACCESS_KEY,
            aws_secret_access_key=Config.S3_SECRET_KEY,
            region_name=Config.S3_REGION
        )

    def upload_file(self, file, filename):
        try:
            self.s3.upload_fileobj(file, Config.S3_BUCKET, filename)
            return f"Archivo subido exitosamente a {Config.S3_BUCKET}/{filename}"
        except NoCredentialsError:
            return "Credenciales de S3 no válidas"