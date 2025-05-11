from __future__ import annotations
import asyncio
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json
from copy import deepcopy
from fastapi import WebSocket
from user import get_id_by_username

DEBUG = True

class TaskStatus(Enum):
    PENDING = "Pending"
    TIMEUP = "Time Up"
    OUTDATED = "Out Dated"

@dataclass
class TaskDate:
    year: int
    month: int
    day: int
    hour: int
    minute: int

    @classmethod
    def from_datetime(cls, dt: datetime) -> TaskDate:
        return cls(dt.year, dt.month, dt.day, dt.hour, dt.minute)
    
    def __str__(self):
        return str(self.year).zfill(4) + str(self.month).zfill(2) + str(self.day).zfill(2) + str(self.hour).zfill(2) + str(self.minute).zfill(2)
    
    def __le__(self, other):
        return int(str(self)) <= int(str(other))
    
    def __lt__(self, other):
        return int(str(self)) < int(str(other))
    
    def __eq__(self, other):
        return int(str(self)) == int(str(other))

class Task:
    def __init__(self, id: int, user_id: int, name: str, description: str, date: TaskDate):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.description = description
        self.date = date
    
    def time_check(self) -> TaskStatus:
        now = TaskDate.from_datetime(datetime.now())
        if self.date < now:
            return TaskStatus.OUTDATED
        elif self.date == now:
            return TaskStatus.TIMEUP
        else:
            return TaskStatus.PENDING

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

        self.active_connections.append({
            "user_id": get_id_by_username(websocket.query_params["username"]),
            "websocket": websocket
            })

    def disconnect(self, websocket: WebSocket):
        self.active_connections = [x for x in self.active_connections if x["websocket"] != websocket]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection["websocket"].send_text(message)

class TaskManager():
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        with open("tasks.json", "r") as file:
            self._tasks = json.load(file)
        self._async_task = asyncio.get_event_loop().create_task(self._check_tasks_loop())

    async def connect(self, websocket: WebSocket):
        await self.connection_manager.connect(websocket)
    
    def close(self):
        self._async_task.cancel()
    
    def add_task(self, task: Task) -> None:
        self._tasks.append(task)
    
    def remove_task(self, task: Task) -> None:
        self._tasks.remove(task)
    
    def remove_task(self, task_id: int) -> None:
        for task in self._tasks:
            if task.id == task_id:
                self._tasks.remove(task)
                break
    
    def get_tasks(self) -> list[Task]:
        return deepcopy(self._tasks)

    def get_task(self, task_id: int) -> Task | None:
        for task in self._tasks:
            if task.id == task_id:
                return deepcopy(task)
        return None

    async def _check_to_announce(self, task: Task) -> None:
        if task.time_check() == TaskStatus.TIMEUP:
            for connection in self.connection_manager.active_connections:
                if connection["user_id"] == task.user_id:
                    await self.connection_manager.send_personal_message(
                        f"Task {task.name} is time up!", connection["websocket"])

    async def _check_tasks_loop(self) -> None:
        while True:
            for task in self._tasks:
                await self._check_to_announce(task)
            await asyncio.sleep(60)
