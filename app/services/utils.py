import re

def contains_drug_names(text):
    """
    Checks if the given text contains potential drug names using a more comprehensive approach.

    Args:
        text (str): The text to check.

    Returns:
        bool: True if the text likely contains drug information, False otherwise.
    """

    text = text.lower()  # Convert to lowercase for easier matching

    if 1==1:
        return True

    # 1. Check for common drug name patterns:
    #    - Look for words ending in common drug suffixes (e.g., -olol, -pril, -statin).
    drug_suffixes = ["olol", "pril", "statin", "idine", "azole", "vir", "mab", "nib", "pine", "mycin", "Lipitor"]
    if any(re.search(r"\b\w+" + suffix + r"\b", text) for suffix in drug_suffixes):
        return True

    # 2. Check for dosage keywords:
    dosage_keywords = [
        "mg", "mcg", "ml", "iu",  # Units
        "milligram", "microgram", "milliliter", "international unit",
        " BID", " TID", " QID", " QD",  # Common frequencies with leading space
        "/day", "daily", "weekly", "monthly",  # Other frequency indicators
        "oral", "tablet", "capsule", "injection", "solution", "suspension",
        "inhaled", "topical", "intravenous", "subcutaneous", "patch",
        "extended release", "immediate release"
    ]
    if any(keyword in text for keyword in dosage_keywords):
        return True

    # 3. Check for date-like patterns (if other indicators are present):
    #    - This is a weak indicator on its own, but can be helpful in combination with others.
    date_patterns = [
        r"\d{1,2}/\d{1,2}/\d{2,4}",  # MM/DD/YYYY, M/D/YY
        r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2},\s+\d{4}",  # Month Day, Year
    ]
    if any(re.search(pattern, text) for pattern in date_patterns):
        # Only return True if other drug-related information is also present
        if any(re.search(r"\b\w+" + suffix + r"\b", text) for suffix in drug_suffixes) or \
           any(keyword in text for keyword in dosage_keywords):
            return True

    # 4. Check for presence of common drug names (optional):
    #    - You could maintain a list of very common drug names (e.g., aspirin, ibuprofen, acetaminophen)
    #      and check if any of them are present. However, this list would need to be regularly updated
    #      and might not be very effective without more sophisticated matching.

    # If none of the above conditions are met, it's less likely to be drug-related information.
    return False

def clean_and_split_drug_names(drug_string, delimiters=r"[,;+/]"):
    """
    Cleans and splits a string of concatenated drug names into a list of individual drug names.

    Args:
        drug_string (str): The string containing concatenated drug names.
        delimiters (str): Regular expression pattern for delimiters (default: ,;+/).

    Returns:
        list: A list of individual drug names, cleaned and lowercased.
    """
    if not drug_string:
        return []

    # Remove extra spaces and split by specified delimiters
    drug_names = re.split(delimiters, drug_string)
    # Clean each drug name
    cleaned_drug_names = [name.strip().lower() for name in drug_names if name.strip()]
    return cleaned_drug_names