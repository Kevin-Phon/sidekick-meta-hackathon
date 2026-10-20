from dataclasses import dataclass
from pathlib import Path

@dataclass
class Settings:
    data_dir: Path
    timezone: str = 'America/Los_Angeles'
    demo_mode: bool = False
    run_scheduler: bool = False
