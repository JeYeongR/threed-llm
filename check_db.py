import pymysql
from database import init_db, db_tunnel

def check_table_structure():
    init_db()
    
    try:
        conn_params = db_tunnel.get_connection_params()
        
        connection = pymysql.connect(
            host=conn_params['host'],
            user=conn_params['user'],
            password=conn_params['password'],
            database=conn_params['db'],
            port=conn_params['port'],
            charset='utf8mb4'
        )
        
        print("데이터베이스에 성공적으로 연결되었습니다.")
    except Exception as e:
        print(f"데이터베이스 연결 오류: {str(e)}")
        return
        
    try:
        with connection.cursor() as cursor:
            # 테이블 목록 확인
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print("테이블 목록:")
            for table in tables:
                print(table[0])
            
            # company_posts 테이블 구조 확인
            cursor.execute("DESCRIBE company_posts")
            columns = cursor.fetchall()
            print("\ncompany_posts 테이블 구조:")
            for column in columns:
                print(f"이름: {column[0]}, 타입: {column[1]}, Null 허용: {column[2]}, 키: {column[3]}, 기본값: {column[4]}, 추가정보: {column[5]}")
                
            # posts 테이블 구조 확인
            cursor.execute("DESCRIBE posts")
            columns = cursor.fetchall()
            print("\nposts 테이블 구조:")
            for column in columns:
                print(f"이름: {column[0]}, 타입: {column[1]}, Null 허용: {column[2]}, 키: {column[3]}, 기본값: {column[4]}, 추가정보: {column[5]}")
        
        # 연결 닫기
        connection.close()
    except Exception as e:
        print(f"오류 발생: {str(e)}")

if __name__ == "__main__":
    check_table_structure()
