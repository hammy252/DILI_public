import pandas as pd
from config import Config
import logging
from fuzzywuzzy import fuzz

import sys
import os

# Get the absolute path of the project's root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Add the project root to the Python path
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def get_dili_risk_from_excel(medication_list):
    """
    Retrieves DILI risk information for a list of medications from the Combined.xlsx file.

    Args:
        medication_list (list): A list of dictionaries, where each dictionary represents a medication
                                and contains at least the 'normalized_name' key.

    Returns:
        list: A list of dictionaries, where each dictionary contains DILI risk information
              for a medication.
    """
    try:
        # Load combined data from the specified sheet
        logging.info(f"Loading combined DILI data from: {Config.COMBINED_FILE}, Sheet: 'Sheet1'")
        combined_df = pd.read_excel(Config.COMBINED_FILE, sheet_name='Sheet1')  # Specify sheet name
        logging.info(f"Successfully loaded combined DILI data.")

        # Rename columns for consistency
        combined_df.rename(columns={
            'Drug Name': 'Drug',  # Keep this if your column is still named 'Drug Name'
            'vDILIConcern': 'DILI_Likelihood',
            'Livertox Score': 'LiverTox_LikelihoodScore'  # Match the exact column name
        }, inplace=True)

        dili_risk_data = []

        for medication in medication_list:
            drug_name = medication['normalized_name'].lower()

            # Find the best match using fuzzy matching
            best_match = None
            best_score = 0
            for index, row in combined_df.iterrows():
                score = fuzz.ratio(drug_name, str(row['Drug']).lower())  # Convert to string before lowercasing
                #logging.info(f"  Comparing to: {row['Drug']}, Score: {score}")
                if score > best_score:
                    best_score = score
                    best_match = row

            # Set a threshold for matching (e.g., 85%)
            if best_match is not None and best_score >= 85:
                combined_info = best_match.to_dict()
                logging.info(f"Found match for {drug_name}: {combined_info['Drug']} (score: {best_score})")
            else:
                combined_info = {
                    'Drug': drug_name,
                    'DILI_Likelihood': 'Unknown - no match',
                    'LiverTox_LikelihoodScore': 'Unknown - no match'
                }
                logging.warning(f"No close match found for drug: {drug_name} (best score: {best_score if best_match is not None else 0} - compared to: {row['Drug'].lower() if best_match is not None else ''})")

            dili_risk_data.append(combined_info)

        return dili_risk_data

    except FileNotFoundError:
        logging.error(f"Error: Combined Excel file not found: {Config.COMBINED_FILE}")
        return []
    except Exception as e:
        logging.error(f"An error occurred while processing DILI risk data: {e}", exc_info=True)
        return []