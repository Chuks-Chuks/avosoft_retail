from faker import Faker
import random
from ..config import SETTINGS

fake = Faker()
Faker.seed(SETTINGS.seed)
random.seed(SETTINGS.seed)

class BaseGenerator:
    def __init__(self): ...
    @staticmethod
    def day(ds: str | None, fallback: str):
        return ds or fallback
