from dataclasses import dataclass
from typing import List
from task import Task


@dataclass
class User:
    name: str
    password: str

