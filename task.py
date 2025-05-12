from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum, auto
import json
from typing import List, Dict, Optional, Any
from fastapi import WebSocket
from user import get_id_by_username

class TaskStatus(Enum):
    """任务状态枚举类"""
    PENDING = auto()
    TIMEUP = auto()
    OUTDATED = auto()

    def __str__(self) -> str:
        return self.name.title()

@dataclass
class TaskDate:
    """表示任务日期和时间的数据类"""
    year: int
    month: int
    day: int
    hour: int
    minute: int

    @classmethod
    def from_datetime(cls, dt: datetime) -> TaskDate:
        """从datetime对象创建TaskDate"""
        return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute)
    
    def to_datetime(self) -> datetime:
        """转换为datetime对象"""
        return datetime(self.year, self.month, self.day, self.hour, self.minute)
    
    def add_days(self, days: int) -> None:
        """添加天数"""
        dt = self.to_datetime() + timedelta(days=days)
        self.year = dt.year
        self.month = dt.month
        self.day = dt.day
    
    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d} {self.hour:02d}:{self.minute:02d}"

    def __lt__(self, other: TaskDate) -> bool:
        return self.to_datetime() < other.to_datetime()
    
    def __le__(self, other: TaskDate) -> bool:
        return self.to_datetime() <= other.to_datetime()
    
    def __eq__(self, other: TaskDate) -> bool:
        return self.to_datetime() == other.to_datetime()

class Task:
    """任务类，代表一个提醒任务"""
    def __init__(self, id: int, user_id: int, name: str, description: str, 
                 date: TaskDate, repeat_days: Optional[int] = None, 
                 repeat_count: Optional[int] = None):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.description = description
        self.date = date
        self.repeat_days = repeat_days
        self.repeat_count = repeat_count
    
    def time_check(self) -> TaskStatus:
        """检查任务状态"""
        now = TaskDate.from_datetime(datetime.now())
        if self.date < now:
            return TaskStatus.OUTDATED
        elif self.date == now:
            return TaskStatus.TIMEUP
        return TaskStatus.PENDING
    
    def update_next_occurrence(self) -> bool:
        """更新下次执行时间，返回是否还有下次执行"""
        if not self.repeat_days:
            return False
        
        self.date.add_days(self.repeat_days)
        
        if self.repeat_count is not None:
            self.repeat_count -= 1
            return self.repeat_count > 0
        return True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式用于JSON序列化"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "date": asdict(self.date),
            "repeat_days": self.repeat_days,
            "repeat_count": self.repeat_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Task:
        """从字典创建任务实例"""
        date_data = data.pop("date")
        return cls(**data, date=TaskDate(**date_data))

class ConnectionManager:
    """管理WebSocket连接"""
    def __init__(self):
        self.active_connections: List[Dict[str, Any]] = []

    async def connect(self, websocket: WebSocket) -> None:
        """建立新的WebSocket连接"""
        await websocket.accept()
        self.active_connections.append({
            "user_id": get_id_by_username(websocket.query_params["username"]),
            "websocket": websocket
        })

    def disconnect(self, websocket: WebSocket) -> None:
        """断开WebSocket连接"""
        self.active_connections = [
            x for x in self.active_connections 
            if x["websocket"] != websocket
        ]

class TaskManager:
    """任务管理器，负责任务的存储和检查"""
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self._tasks: List[Task] = []
        self._load_tasks()
        self._async_task = asyncio.get_event_loop().create_task(self._check_tasks_loop())

    def _load_tasks(self) -> None:
        """从JSON文件加载任务"""
        try:
            with open("tasks.json", "r") as file:
                tasks_data = json.load(file)
                self._tasks = [Task.from_dict(task_data) for task_data in tasks_data]
        except (FileNotFoundError, json.JSONDecodeError):
            self._tasks = []
    
    def _save_tasks(self) -> None:
        """保存任务到JSON文件"""
        with open("tasks.json", "w") as file:
            json.dump([task.to_dict() for task in self._tasks], file, indent=4)

    async def connect(self, websocket: WebSocket) -> None:
        """处理新的WebSocket连接"""
        await self.connection_manager.connect(websocket)
    
    def disconnect(self, websocket: WebSocket) -> None:
        """处理WebSocket断开连接"""
        self.connection_manager.disconnect(websocket)
    
    def close(self) -> None:
        """关闭任务管理器"""
        self._async_task.cancel()
        self._save_tasks()
    
    def add_task(self, task: Task) -> None:
        """添加新任务"""
        self._tasks.append(task)
        self._save_tasks()
    
    def remove_task(self, task_id: int) -> None:
        """移除任务"""
        self._tasks = [task for task in self._tasks if task.id != task_id]
        self._save_tasks()
    
    def get_tasks(self) -> List[Task]:
        """获取所有任务的副本"""
        return self._tasks.copy()

    def get_tasks_by_user_id(self, user_id: int) -> List[Task]:
        """获取指定用户的所有任务"""
        return [task for task in self._tasks if task.user_id == user_id]

    def get_task(self, task_id: int) -> Optional[Task]:
        """获取指定ID的任务"""
        for task in self._tasks:
            if task.id == task_id:
                return task
        return None

    async def _check_to_announce(self, task: Task) -> None:
        """检查并发送任务提醒"""
        if task.time_check() == TaskStatus.TIMEUP:
            for conn in self.connection_manager.active_connections:
                if conn["user_id"] == task.user_id:
                    await conn["websocket"].send_text(
                        f"提醒: 任务 '{task.name}' 时间到了！\n{task.description}"
                    )
            
            if not task.update_next_occurrence():
                self.remove_task(task.id)

    async def _check_tasks_loop(self) -> None:
        """定期检查任务状态的循环"""
        while True:
            for task in self._tasks.copy():
                await self._check_to_announce(task)
            await asyncio.sleep(6)
