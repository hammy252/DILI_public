import os
import json
import time
import logging
from groq import Groq, APIConnectionError, RateLimitError, APIStatusError, APIResponseValidationError
from app.services.utils import contains_drug_names, clean_and_split_drug_names
from config import Config

import sys

# Get the absolute path of the project's root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # Go up two levels from this file

# Add the project root to the Python path
sys.path.insert(0, project_root)

logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
medication_counts = {}
total_medications_processed = 0
total_meds=0

def extract_medications_from_groq(user_input, model):
    """
    Extracts medication information (including individual dates) from unstructured text using the Groq API.

    Args:
        user_input (str): Unstructured text containing medication names, dosages, frequencies, and dates.
        model (str): The Groq model to use.

    Returns:
        list: A list of dictionaries, where each dictionary represents a medication
              and contains the keys 'name', 'normalized_name', 'dosage', 'frequency', and 'date'.
              Returns None if an error occurs.
    """
    if not user_input or not isinstance(user_input, str):
        logging.error("User input must be a non-empty string.")
        raise ValueError("User input must be a non-empty string.")

    global medication_counts
    global total_medications_processed
    client = Groq(api_key=Config.GROQ_API_KEY)

    system_prompt = """
    You are a medical expert system. Extract the medication names, dosages, frequencies, and their associated dates from the following unstructured text.
    Normalize the medication names to their most common or standardized form. Make sure the medication names are in common name. Must be a directed JSON, no data in front of the result.
    Return the results as a JSON array of objects, where each object has the keys 'name', 'normalized_name', 'dosage', 'frequency', and 'date'. All letter in normalized name must be all lowercase.If the input text does not contain any medication information, return an empty JSON array ( [] ).
If no matching, can use the the same word for name, and N/A for normalized_name  If dosage, frequency, or date is not found, use null. Do not provide any conversational filler, only JSON output.
    """

    user_prompt = f"""
    Unstructured Text:
    {user_input}

    JSON Output:
    """

    try:
        # Introduce a 2-second delay before the API call
        time.sleep(2)

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=model,
            max_tokens=5000,
            temperature=0.2,
            response_format={ "type": "json_object" }
        )

        medication_json_str = chat_completion.choices[0].message.content
        logging.info(f"Raw response content: {medication_json_str}")

        if not medication_json_str:
            logging.error("No medication information extracted by Groq API (empty response).")
            return None

        try:
            response_data = json.loads(medication_json_str)
            if "medications" in response_data:
                medication_list = response_data["medications"]
            elif isinstance(response_data, list):
                medication_list = response_data
            else:
                logging.error("Invalid response format: Expected a list or a dictionary with a 'medications' key.")
                return None

        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON response from Groq API: {e}")
            return None

        # Validate the structure of each medication object
        for medication in medication_list:
            if not isinstance(medication, dict):
                logging.error("Invalid medication format in response (not a dictionary).")
                return None
            required_keys = ["name", "normalized_name"]  # Only require name and normalized_name
            if not all(key in medication for key in required_keys):
                logging.error(f"Missing required keys in medication: {medication}")
                return None
            # Log if optional keys are null
            for key in ["dosage", "frequency", "date"]:
                if key in medication and medication[key] is None:
                    logging.info(f"Optional key '{key}' is null for medication: {medication['name']}")

            # Update medication counts
            normalized_name = medication['normalized_name'].lower()
            medication_counts[normalized_name] = medication_counts.get(normalized_name, 0) + 1
            total_medications_processed += 1
        return medication_list

    except APIConnectionError as e:
        logging.error(f"The server could not be reached: {e.__cause__}")
        return None
    except RateLimitError as e:
        logging.error(f"A 429 status code was received (rate limit exceeded); we should back off a bit: {e}")
        return None
    except APIStatusError as e:
        logging.error(f"Another non-200-range status code was received: {e.status_code} - {e.response}")
        return None
    except APIResponseValidationError as e:
        logging.error(f"Response validation error: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None

def log_medication_counts():
    logging.info("Medication Counts:")
    for drug, count in medication_counts.items():
        logging.info(f"  {drug}: {count}")
    logging.info(f"Total medications processed: {total_medications_processed}")