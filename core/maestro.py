from enum import Enum
from dataclasses import dataclass
import sys
from pathlib import Path
import FastAPI

sys.path.append(str(Path(__file__).resolve().parents[1]))

from data import data_provider
from data import cache_manager
from data import market_calculator
from core import regime_guardian
from config import settings

@dataclass
class Maestro:
    
    def __post_init__(self):
        self.cache = cache_manager.CacheManager()
        self.mc = market_calculator.MarketCalculator()
        self.rg = regime_guardian.RegimeGuardian()
        self.dp = data_provider.DataProvider()
    
    
    def start():
        """Starts the actual workflow
         1-> Get the user configs for symbols
         2-> Fetch the relevant data
         3-> Calculate the market 
         4-> With the data & calculation decide regime and veto if needed
         5-> Prepare data for the agents
        """
        maestro = Maestro()
        
        
        