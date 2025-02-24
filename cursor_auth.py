import sqlite3
import os
import sys
from colorama import Fore, Style, init

# 初始化colorama
init()

# 定义emoji和颜色常量
EMOJI = {
    'DB': '🗄️',
    'UPDATE': '🔄',
    'SUCCESS': '✅',
    'ERROR': '❌',
    'WARN': '⚠️',
    'INFO': 'ℹ️',
    'FILE': '📄',
    'KEY': '🔐'
}

class CursorAuth:
    def __init__(self, translator=None):
        self.translator = translator
        # 判断操作系统
        if os.name == "nt":  # Windows
            self.db_path = os.path.join(
                os.getenv("APPDATA"), "Cursor", "User", "globalStorage", "state.vscdb"
            )
        else:  # macOS
            self.db_path = os.path.expanduser(
                "~/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
            )

        # 检查数据库文件是否存在
        if not os.path.exists(self.db_path):
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('auth.db_not_found', path=self.db_path)}{Style.RESET_ALL}")
            return

        # 检查文件权限
        if not os.access(self.db_path, os.R_OK | os.W_OK):
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('auth.db_permission_error')}{Style.RESET_ALL}")
            return

        try:
            self.conn = sqlite3.connect(self.db_path)
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('auth.connected_to_database')}{Style.RESET_ALL}")
        except sqlite3.Error as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('auth.db_connection_error', error=str(e))}{Style.RESET_ALL}")
            return

    def update_auth(self, email=None, access_token=None, refresh_token=None):
        conn = None
        try:
            # 确保目录存在并设置正确权限
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, mode=0o755, exist_ok=True)
            
            # 如果数据库文件不存在，创建一个新的
            if not os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ItemTable (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                ''')
                conn.commit()
                if sys.platform != "win32":
                    os.chmod(self.db_path, 0o644)
                conn.close()

            # 重新连接数据库
            conn = sqlite3.connect(self.db_path)
            print(f"{EMOJI['INFO']} {Fore.GREEN} {self.translator.get('auth.connected_to_database')}{Style.RESET_ALL}")
            cursor = conn.cursor()
            
            # 增加超时和其他优化设置
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            
            # 设置要更新的键值对
            updates = []
            if email is not None:
                updates.append(("cursorAuth/cachedEmail", email))
            if access_token is not None:
                updates.append(("cursorAuth/accessToken", access_token))
            if refresh_token is not None:
                updates.append(("cursorAuth/refreshToken", refresh_token))
                updates.append(("cursorAuth/cachedSignUpType", "Auth_0"))

            # 使用事务来确保数据完整性
            cursor.execute("BEGIN TRANSACTION")
            try:
                for key, value in updates:
                    # 检查键是否存在
                    cursor.execute("SELECT COUNT(*) FROM ItemTable WHERE key = ?", (key,))
                    if cursor.fetchone()[0] == 0:
                        cursor.execute("""
                            INSERT INTO ItemTable (key, value) 
                            VALUES (?, ?)
                        """, (key, value))
                    else:
                        cursor.execute("""
                            UPDATE ItemTable SET value = ?
                            WHERE key = ?
                        """, (value, key))
                    print(f"{EMOJI['INFO']} {Fore.CYAN} {self.translator.get('auth.updating_pair')} {key.split('/')[-1]}...{Style.RESET_ALL}")
                
                cursor.execute("COMMIT")
                print(f"{EMOJI['SUCCESS']} {Fore.GREEN}{self.translator.get('auth.database_updated_successfully')}{Style.RESET_ALL}")
                return True
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                raise e

        except sqlite3.Error as e:
            print(f"\n{EMOJI['ERROR']} {Fore.RED} {self.translator.get('auth.database_error', error=str(e))}{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"\n{EMOJI['ERROR']} {Fore.RED} {self.translator.get('auth.an_error_occurred', error=str(e))}{Style.RESET_ALL}")
            return False
        finally:
            if conn:
                conn.close()
                print(f"{EMOJI['DB']} {Fore.CYAN} {self.translator.get('auth.database_connection_closed')}{Style.RESET_ALL}")


