from flask import Blueprint, request, jsonify
from app.services.medication_extractor import extract_medications_from_groq
from app.services.dili_connector import get_dili_risk_from_excel
from config import Config
import logging
from queue import Queue, Empty, Full
import threading

bp = Blueprint('routes', __name__)

# In-memory queue for API requests
api_queue = Queue(maxsize=10)  # Max 10 items in the queue
backup_queue = Queue(maxsize=10)

def process_queue(queue, model):
    """
    Worker function to process requests from the queue.
    """
    while True:
        try:
            item = queue.get(timeout=600)  # Get item from queue with a timeout
            if item is None:  # Use None as a signal to stop the worker
                break
            user_input, result_container = item  # Remove model from here
            try:
                medication_list = extract_medications_from_groq(user_input, model=model)
                if medication_list:
                    dili_risk_data = get_dili_risk_from_excel(medication_list)
                    for medication in medication_list:
                        drug_name = medication['normalized_name']
                        for risk_entry in dili_risk_data:
                            if risk_entry['Drug'] == drug_name:
                                medication.update(risk_entry)
                                break  # Stop searching after finding the first match
                    result_container['result'] = medication_list
                else:
                    result_container['result'] = []
            except Exception as e:
                logging.error(f"Error processing medication extraction: {e}", exc_info=True)
                result_container['error'] = str(e)
            finally:
                queue.task_done()
        except Empty:
            continue

# Start the background thread to process the queue
queue_thread = threading.Thread(target=process_queue, args=(api_queue, Config.MODEL), daemon=True)
queue_thread.start()

# Start the background thread to process the backup queue
backup_queue_thread = threading.Thread(target=process_queue, args=(backup_queue, Config.BACKUP_MODEL), daemon=True)
backup_queue_thread.start()

@bp.route('/process_medications', methods=['POST'])
def process_medications():
    data = request.get_json()
    user_input = data.get('user_input')
    model = data.get('model', Config.MODEL)

    logging.info(f"Received request - User input: {user_input}, Model: {model}")

    if not user_input or user_input.strip() == "":
        return jsonify({'data': []}), 200  # Return empty list for empty input

    result_container = {}
    try:
        if model == Config.MODEL:
            api_queue.put((user_input, result_container), block=False)
            api_queue.join()  # Wait for the primary task to be processed
        elif model == Config.BACKUP_MODEL:
            backup_queue.put((user_input, result_container), block=False)
            backup_queue.join()  # Wait for the backup task to be processed
        else:
            return jsonify({'error': f'Model {model} is not supported'}), 400
        if 'result' in result_container:
            return jsonify({'message': 'Medications processed successfully', 'data': result_container['result']}), 200
        else:
            return jsonify({'error': result_container.get('error', 'Failed to process medications')}), 500

    except Full:
        logging.warning(f"Primary queue full, attempting to use backup model: {Config.BACKUP_MODEL}")
        try:
            backup_queue.put((user_input, Config.BACKUP_MODEL, result_container), block=False)
            backup_queue.join()

            if 'result' in result_container:
                return jsonify({'message': 'Medications processed successfully with backup model', 'data': result_container['result']}), 200
            else:
                return jsonify({'error': result_container.get('error', 'Failed to process medications with backup model')}), 500

        except Full:
            return jsonify({'error': 'Both primary and backup queues are full, please try again later'}), 503