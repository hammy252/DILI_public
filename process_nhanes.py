import pandas as pd
from app.services.medication_extractor import extract_medications_from_groq
from app.services.dili_connector import get_dili_risk_from_excel
from app.services.utils import clean_and_split_drug_names
from config import Config
import logging
import time
from fuzzywuzzy import fuzz

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def evaluate_extraction(extracted_medications, drug_concat_list):
    """
    Evaluates the medication extraction performance using fuzzy matching.

    Args:
        extracted_medications (list): List of dictionaries containing extracted medication information.
        drug_concat_list (list): List of drug names from the drug_concat column.

    Returns:
        tuple: (true_positives, false_positives, false_negatives)
    """
    true_positives = 0
    false_positives = 0
    false_negatives = 0

    extracted_names = {med['normalized_name'].lower() for med in extracted_medications}
    expected_names = {name.lower() for name in drug_concat_list}

    # Use fuzzy matching to compare names
    for extracted_name in extracted_names:
        best_match_score = 0
        for expected_name in expected_names:
            score = fuzz.ratio(extracted_name, expected_name)
            if score > best_match_score:
                best_match_score = score

        if best_match_score >= 85:  # Adjust threshold as needed
            true_positives += 1
        else:
            false_positives += 1

    for expected_name in expected_names:
        match_found = False
        for extracted_name in extracted_names:
            score = fuzz.ratio(expected_name, extracted_name)
            if score >= 85:  # Same threshold as above
                match_found = True
                break
        if not match_found:
            false_negatives += 1

    return true_positives, false_positives, false_negatives

def process_nhanes_data(input_file, output_file):
    """
    Processes the NHANES data in the input CSV file, extracts medications from the 'drug_concat' column,
    assesses DILI risk, and adds the results to new columns in the output CSV file.

    Args:
        input_file (str): Path to the input CSV file.
        output_file (str): Path to the output CSV file.
    """
    try:
        logging.info(f"Loading NHANES data from: {input_file}")
        df = pd.read_csv(input_file)
        logging.info(f"Successfully loaded NHANES data. Number of rows: {len(df)}")

        if 'drug_concat' not in df.columns:
            logging.error("Error: 'drug_concat' column not found in the input CSV.")
            return

        # Create new columns for DILI and LiverTox risk
        df['DILIrank_Risk'] = ''
        df['LiverTox_Risk'] = ''

        all_tp = 0
        all_fp = 0
        all_fn = 0

        processed_rows = 0
        for index, row in df.iterrows():
            drug_concat_str = str(row['drug_concat'])
            individual_drugs = clean_and_split_drug_names(drug_concat_str)
            logging.info(f"Processing row {index + 1}: {drug_concat_str} -> {individual_drugs}")

            dilirank_risks = []
            livertox_risks = []

            # Extract medications using Groq API
            try:
                medication_info = extract_medications_from_groq(drug_concat_str, model=Config.MODEL)
                time.sleep(2)  # Rate limiting: 2-second delay between API calls
            except Exception as e:
                logging.error(f"Error extracting medications from Groq API for row {index + 1}: {e}", exc_info=True)
                medication_info = []  # Handle API extraction errors gracefully

            if medication_info:
                # Evaluate extraction performance
                tp, fp, fn = evaluate_extraction(medication_info, individual_drugs)
                all_tp += tp
                all_fp += fp
                all_fn += fn

                for medication in medication_info:
                    # Get DILI risk information from the combined Excel file
                    normalized_drug_name = medication.get('normalized_name', '').lower()
                    dili_risk_data = get_dili_risk_from_excel([{'normalized_name': normalized_drug_name}])

                    if dili_risk_data:
                        dili_info = dili_risk_data[0]
                        dilirank_risks.append(str(dili_info.get('DILI_Likelihood', 'Unknown')))
                        livertox_risks.append(str(dili_info.get('LiverTox_LikelihoodScore', 'Unknown')))
                    else:
                        dilirank_risks.append('Unknown')
                        livertox_risks.append('Unknown')
            else:
                logging.warning(f"No medication information extracted for row: {index + 1}")
                dilirank_risks.append('Unknown')
                livertox_risks.append('Unknown')

            # Combine risks for multiple drugs (if any)
            df.loc[index, 'DILIrank_Risk'] = ', '.join(dilirank_risks)
            df.loc[index, 'LiverTox_Risk'] = ', '.join(livertox_risks)

            processed_rows += 1
            if processed_rows % 100 == 0:
                logging.info(f"Processed {processed_rows} rows out of {len(df)}")

        # Calculate overall precision, recall, and F1-score
        precision = all_tp / (all_tp + all_fp) if (all_tp + all_fp) > 0 else 0
        recall = all_tp / (all_tp + all_fn) if (all_tp + all_fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        logging.info(f"Overall Medication Extraction Performance:")
        logging.info(f"  Precision: {precision:.2f}")
        logging.info(f"  Recall: {recall:.2f}")
        logging.info(f"  F1-score: {f1:.2f}")

        logging.info(f"Saving results to: {output_file}")
        df.to_csv(output_file, index=False)
        logging.info("Processing complete.")

    except FileNotFoundError:
        logging.error(f"Error: Input file not found: {input_file}")
    except Exception as e:
        logging.error(f"An error occurred during processing: {e}", exc_info=True)

if __name__ == "__main__":
    process_nhanes_data(Config.NHANES_INPUT_FILE, Config.OUTPUT_FILE)