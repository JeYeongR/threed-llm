import logging
import os
import uuid
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class S3Uploader:

    def __init__(self):
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.s3_bucket = os.getenv("S3_BUCKET_NAME")
        self.s3_region = os.getenv("AWS_REGION", "ap-northeast-2")
        self.cdn_url = os.getenv("CDN_URL")
        self.s3_client = None

        if not all([self.aws_access_key, self.aws_secret_key, self.s3_bucket]):
            logger.warning("AWS 자격 증명 또는 버킷 이름이 설정되지 않았습니다.")
        else:
            self._init_s3_client()

    def _init_s3_client(self):
        try:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.s3_region,
            )
            logger.info("S3 클라이언트가 성공적으로 초기화되었습니다.")
        except Exception as e:
            logger.error(f"S3 클라이언트 초기화 중 오류 발생: {str(e)}")
            self.s3_client = None

    def upload_image(self, image_data, company_name=None, original_filename=None):
        if self.s3_client is None:
            logger.error("S3 클라이언트가 초기화되지 않았습니다.")
            return None

        try:
            extension = self._get_file_extension(original_filename)
            key = self._generate_s3_key(company_name, extension)

            self._upload_to_s3(image_data, key, extension)

            url = f"https://{self.cdn_url}/{key}"
            logger.info(f"이미지가 S3에 성공적으로 업로드되었습니다: {url}")
            return url

        except ClientError as e:
            logger.error(f"S3 업로드 중 오류 발생: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"이미지 업로드 중 예상치 못한 오류 발생: {str(e)}")
            return None

    def _get_file_extension(self, original_filename):
        extension = "jpg"
        if original_filename and "." in original_filename:
            extension = original_filename.split(".")[-1].lower()
        return extension

    def _generate_s3_key(self, company_name, extension):
        unique_filename = f"{uuid.uuid4()}.{extension}"

        if company_name:
            return f"thumbnails/{company_name}/{unique_filename}"
        else:
            return f"thumbnails/{unique_filename}"

    def _upload_to_s3(self, image_data, key, extension):
        self.s3_client.upload_fileobj(
            BytesIO(image_data),
            self.s3_bucket,
            key,
            ExtraArgs={"ContentType": f"image/{extension}"},
        )


s3_uploader = S3Uploader()
