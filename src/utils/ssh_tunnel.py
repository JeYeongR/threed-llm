import logging
import os

from dotenv import load_dotenv
from sshtunnel import SSHTunnelForwarder

load_dotenv()

logger = logging.getLogger(__name__)


class DBTunnel:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBTunnel, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.tunnel = None
        self.local_bind_port = 3307

    def start(self):

        if self.tunnel is not None and self.tunnel.is_active:
            logger.info("SSH 터널이 이미 실행 중입니다.")
            return True

        try:
            ec2_public_ip = os.getenv("EC2_PUBLIC_IP")
            ssh_username = "ubuntu"
            ssh_pkey = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "threed.pem",
            )

            rds_endpoint = os.getenv("DB_HOST")
            rds_port = int(os.getenv("DB_PORT", "3306"))

            logger.info(
                f"SSH 터널을 시작합니다: {ec2_public_ip}를 통해 {rds_endpoint}:{rds_port}로"
            )

            self.tunnel = SSHTunnelForwarder(
                (ec2_public_ip, 22),
                ssh_username=ssh_username,
                ssh_pkey=ssh_pkey,
                remote_bind_address=(rds_endpoint, rds_port),
                local_bind_address=("127.0.0.1", self.local_bind_port),
            )

            self.tunnel.start()
            logger.info(f"SSH 터널이 시작되었습니다. 로컬 포트: {self.local_bind_port}")
            return True

        except Exception as e:
            logger.error(f"SSH 터널 시작 중 오류 발생: {str(e)}")
            if self.tunnel:
                self.tunnel.stop()
                self.tunnel = None
            return False

    def stop(self):

        if self.tunnel is not None:
            self.tunnel.stop()
            self.tunnel = None
            logger.info("SSH 터널이 중지되었습니다.")

    def get_connection_params(self):

        return {
            "host": "127.0.0.1",
            "port": self.local_bind_port,
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "db": os.getenv("DB_NAME"),
        }

    def __del__(self):

        self.stop()


db_tunnel = DBTunnel()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tunnel = DBTunnel()
    try:
        if tunnel.start():
            logger.info(f"연결 파라미터: {tunnel.get_connection_params()}")
            input("터널이 성공적으로 열렸습니다. 종료하려면 Enter 키를 누르세요...")
    finally:
        tunnel.stop()
