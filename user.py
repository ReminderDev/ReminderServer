import json
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class User:
    """用户类"""
    id: int
    username: str
    password: str

class UserManager:
    """用户管理类"""
    def __init__(self, file_path: str = "users.json"):
        self.file_path = file_path
        self.users: List[User] = []
        self._load_users()

    def _load_users(self) -> None:
        """从JSON文件加载用户数据"""
        try:
            with open(self.file_path, "r") as f:
                users_data = json.load(f)
                self.users = [
                    User(
                        id=user["id"],
                        username=user["username"],
                        password=user["password"]
                    )
                    for user in users_data
                ]
        except (FileNotFoundError, json.JSONDecodeError):
            self.users = []
    
    def verify_user(self, username: str, password: str) -> bool:
        """验证用户凭据"""
        return any(
            user.username == username and user.password == password
            for user in self.users
        )
    
    def get_id_by_username(self, username: str) -> Optional[int]:
        """通过用户名获取用户ID"""
        for user in self.users:
            if user.username == username:
                return user.id
        return None

# 创建全局用户管理器实例
user_manager = UserManager()

def verify_user(username: str, password: str) -> bool:
    """验证用户凭据（全局函数）"""
    return user_manager.verify_user(username, password)

def get_id_by_username(username: str) -> Optional[int]:
    """通过用户名获取用户ID（全局函数）"""
    return user_manager.get_id_by_username(username)
