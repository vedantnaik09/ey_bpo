import pandas as pd
import time
import os

def run_all():
    """
    Continuously checks the status of each phone number in the csv file.
    Calls the first phone number immediately. Calls the next phone number only when
    the previous phone number's status changes to 'called'.
    """
    csv_file_path = "data.csv"
    seen = {}
    phone_numbers_to_call = []

    # Read the CSV file initially to get the list of phone numbers
    try:
        data = pd.read_csv(csv_file_path)
        phone_numbers_to_call = data['Phone Number'].tolist()  # Get the list of phone numbers
    except Exception as e:
        print(f"Error reading the CSV file: {e}")
        return

    # Start calling the first phone number immediately
    if phone_numbers_to_call:
        first_phone_number = phone_numbers_to_call[0]
        print(f"Calling the first phone number: {first_phone_number}")
        os.system(f"lk dispatch create --new-room --agent-name outbound-caller --metadata {first_phone_number}")
        seen[first_phone_number] = "called"
        phone_numbers_to_call = phone_numbers_to_call[1:]  # Remove the first phone number from the list

    while phone_numbers_to_call:
        for phone_number in phone_numbers_to_call:
            try:
                # Read the CSV file to check the status of the phone number
                data = pd.read_csv(csv_file_path)
                row = data[data['Phone Number'] == phone_number]
                status = row['Call Status'].values[0]  # Get the current status
                
                if status == "called" and phone_number not in seen:
                    seen[phone_number] = status
                    
                    # Wait for 10 seconds before calling the next number
                    print(f"Phone number {phone_number} status changed to 'called'. Waiting for 10 seconds...")
                    time.sleep(30)
                    
                    # Call the next phone number
                    print(f"Calling phone number: {phone_number}")
                    os.system(f"lk dispatch create --new-room --agent-name outbound-caller --metadata {phone_number}")
                    
                    # Once the phone number is called, move to the next one
                    phone_numbers_to_call = phone_numbers_to_call[1:]
                    break
                    
            except Exception as e:
                print(f"Error processing phone number {phone_number}: {e}")
        
        # Check the CSV file again after 5 seconds
        time.sleep(5)  # Check every 5 seconds
        
# Example usage:

