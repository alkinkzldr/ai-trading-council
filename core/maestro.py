from enum import Enum
from dataclasses import dataclass
import sys
from pathlib import Path
import FastAPI

sys.path.append(str(Path(__file__).resolve().parents[1]))

from data import data_provider
from data import cache_manager
from data import market_calculator
from config import settings

@dataclass
class Maestro: