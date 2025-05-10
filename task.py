from __future__ import annotations
import asyncio
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json

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
    def __init__(self, name: str, description: str, date: TaskDate):
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

class TaskManager():
    def __init__(self):
        with open("tasks.json", "r") as file:
            self._tasks = json.load(file)
        self._async_task = asyncio.get_event_loop().create_task(self._check_tasks_loop())
    
    def close(self):
        self._async_task.cancel()
    
    def add_task(self, task: Task) -> None:
        self._tasks.append(task)
    
    def remove_task(self, task: Task) -> None:
        self._tasks.remove(task)

    def _check_to_announce(self, task: Task) -> None:
        if task.time_check() == TaskStatus.TIMEUP:
            print(f"YES! It's time to announce the task: {task.name}")
        else:
            print(f"NO! It's not time to announce the task: {task.name}")

    async def _check_tasks_loop(self):
        while True:
            for task in self._tasks:
                self._check_to_announce(task)
            await asyncio.sleep(1)
