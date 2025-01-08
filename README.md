# DILI## Project Structure
The project is organized into the following directories and files:
*   **`app/`:** Contains the main application code.
    *   **`__init__.py`:** Initializes the Flask application.
    *   **`routes.py`:** Defines the API endpoints for the Flask application.
    *   **`services/`:** Contains the core logic for medication extraction and DILI risk assessment.
        *   **`__init__.py`:**  Indicates that `services` is a package.
        *   **`medication_extractor.py`:** Handles medication extraction from unstructured text using the Groq API.
        *   **`dili_connector.py`:** Handles retrieval of DILI risk information from the combined database.
        *   **`utils.py`:** Contains utility functions used by other modules.
*   **`data/`:**  Contains the data files used by the application.
    *   **`Combined.xlsx`:** A manually curated Excel file containing merged DILI risk data from DILIrank and LiverTox.
    *   **`nhanes.csv`:** A CSV file containing sample NHANES data used for testing and evaluation (or a placeholder for your actual NHANES data file).
    *   **`nhanes_dili_risk.csv`:** The output CSV file where processed NHANES data with added DILI risk information will be stored.
*   **`config.py`:** Contains configuration settings for the application (e.g., API keys, file paths, model names).
*   **`requirements.txt`:** Lists the Python dependencies for the project.
*   **`run.py`:** The main script to run the Flask application.
*   **`process_nhanes.py`:** A script to process a CSV file (like NHANES data) and add DILI risk information.
*   **`app.log`:** Log file for application events and errors.

## Configuration (`config.py`)
This module contains the `Config` class, which holds configuration settings for the application.
Variables:
•	API_KEY: API LLM key (required). 
•	MODEL: The default model to use for medication extraction.
•	COMBINED_FILE: The path to the Combined.xlsx file containing DILI risk data.
•	SUPPORTED_MODELS: A list of Groq models that your application supports.
•	NHANES_INPUT_FILE: Default path to an input CSV file that can be processed by process_nhanes.py.
•	OUTPUT_FILE: Default path to an output CSV file where results from process_nhanes.py will be written.
Utility Functions (app/services/utils.py)
This module contains utility functions used by other parts of the application.
Functions:
•	contains_drug_names(text): A heuristic function that checks if a given text string likely contains drug names. It uses a combination of regular expressions and keyword matching to make this determination.
•	clean_and_split_drug_names(drug_string, delimiters=r"[,;+/]"): Cleans and splits a string containing multiple drug names (e.g., from the drug_concat column) into a list of individual drug names. It handles various delimiters, removes extra spaces, and converts names to lowercase.
Medication Extraction (app/services/medication_extractor.py)
This module contains the core function for extracting medication information from unstructured text using the API.
Functions:
•	extract_medications_from_API(user_input, model="###"):
o	Takes unstructured text (user_input) and a model name (model) as input.
o	Constructs a system prompt and a user prompt to instruct the LLM on how to extract medication information.
o	Sends the prompt to the API using client.chat.completions.create().
o	Includes a 2-second delay (time.sleep(2)) before each API call to handle potential rate limiting.
o	Parses the JSON response from the Groq API.
o	Validates the structure of the extracted medication information.
o	Handles various API errors using try...except blocks (e.g., APIConnectionError, RateLimitError, APIStatusError, APIResponseValidationError).
o	Logs the raw response content and any errors encountered.
o	Returns a list of dictionaries, where each dictionary represents a medication with the keys "name", "normalized_name", "dosage", "frequency", and "date". Returns an empty list ([]) if no medications are found and None if an error occurs.
DILI Risk Assessment (app/services/dili_connector.py)
This module contains the function for retrieving DILI risk information from the Combined.xlsx file.
Functions:
•	get_dili_risk_from_excel(medication_list):
o	Takes a list of medication dictionaries (output from extract_medications_from_groq) as input.
o	Loads the Combined.xlsx file (which contains merged data from DILIrank and LiverTox) into a pandas DataFrame.
o	Iterates through the medication_list:
	Converts the normalized_name to lowercase.
	Uses fuzzy matching (fuzzywuzzy library, fuzz.ratio) to find the best match in the "Drug" column of the DataFrame.
	Applies a matching threshold (currently 85).
	If a match is found, retrieves the "DILI_Likelihood" and "LiverTox_LikelihoodScore" values.
	If no match is found, assigns "Unknown" to the DILI risk fields.
o	Returns a list of dictionaries, where each dictionary contains the DILI risk information for a medication.
o	Includes error handling for file not found and other exceptions.
o	Logs warning messages if no close match is found for a drug.
Flask API Routes (app/routes.py)
This module defines the Flask API endpoint for processing medication information.
Functions:
•	process_medications():
o	Handles POST requests to /api/process_medications.
o	Expects a JSON payload with user_input (text) and an optional model field.
o	Implements an in-memory queue (api_queue) to manage incoming requests.
o	Validates the provided model against Config.SUPPORTED_MODELS.
o	Adds the user input, model, and a result_container dictionary to the queue.
o	Uses a separate thread (process_queue_thread) to process the queue.
o	Calls extract_medications_from_groq to extract medications.
o	Calls get_dili_risk_from_excel to get DILI risk data.
o	Combines the extracted medication information with DILI risk data.
o	Returns a JSON response with the combined data or an appropriate error message.
o	Handles queue full errors (HTTP 503).
•	process_queue():
o	Worker function that continuously retrieves requests from the queue.
o	Calls the extract_medications_from_groq and get_dili_risk_from_excel functions to process each request.
o	Updates the result_container with the result or any error.
o	Handles exceptions during processing and logs errors.
NHANES Data Processing (process_nhanes.py):
Functions:
•	process_nhanes_data(input_file, output_file):
o	Reads the NHANES data from the specified input CSV file.
o	Iterates through each row of the DataFrame.
o	Cleans and splits the drug_concat column into individual drug names.
o	Calls extract_medications_from_groq to extract medication information for each drug (simulating the API call in the context of NHANES data).
o	Calls get_dili_risk_from_excel to get DILI risk information.
o	Combines the DILI risk information for all drugs in a row.
o	Appends the combined DILI risk to the DILIrank_Risk and LiverTox_Risk columns.
o	Logs the performance metrics.
o	Saves the updated DataFrame to the specified output CSV file.
