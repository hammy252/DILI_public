
import os
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
load_dotenv()

class Config:
    LLM_API_KEY = ''
    MODEL = ''
    BACKUP_MODEL = ''
    COMBINED_FILE = os.path.join('data', 'combined.xlsx')
    NHANES_INPUT_FILE = 'data/nhanes.csv'
    OUTPUT_FILE = 'data/nhanes_dili_risk.csv'
