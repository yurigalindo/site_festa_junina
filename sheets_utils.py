import datetime
import os
from dotenv import load_dotenv

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

# Placeholder for Google API credentials and Sheet ID
# These should be loaded from environment variables or a config file in a real application
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
DEFAULT_SHEET_NAME = 'Sheet1' # Or your desired sheet name

def append_to_sheet(data):
    """
    Appends a row of data to the configured Google Sheet using a service account.

    Args:
        data (list): A list of values to append as a new row. 
                     Expected order: timestamp, city, group, num_people, 
                                     names_str, veg_options_str, phone, 
                                     amount, pix_desc.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    if not GOOGLE_SHEET_ID:
        print("Error: GOOGLE_SHEET_ID environment variable not set.")
        return False
    if not GOOGLE_SERVICE_ACCOUNT_FILE:
        print("Error: GOOGLE_SERVICE_ACCOUNT_FILE environment variable not set.")
        return False

    print(f"Attempting to append to Google Sheet ID: {GOOGLE_SHEET_ID}")
    print(f"Using service account file: {GOOGLE_SERVICE_ACCOUNT_FILE}")
    print(f"Data to append: {data}")

    creds = None
    try:
        creds = Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
    except FileNotFoundError:
        print(f"Error: Service account credentials file not found at {GOOGLE_SERVICE_ACCOUNT_FILE}")
        return False
    except Exception as e:
        print(f"Error loading service account credentials: {e}")
        return False

    try:
        service = build('sheets', 'v4', credentials=creds)

        # Determine the range to append to. Appends after the last row with data in the sheet.
        # Example: 'Sheet1' will append to the first empty row of Sheet1.
        # Or specify a range like 'Sheet1!A1' but API will still append after last data within that table.
        sheet_range = f"{DEFAULT_SHEET_NAME}" 

        body = {
            'values': [data]  # Data needs to be a list of lists for rows
        }
        result = service.spreadsheets().values().append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=sheet_range,  # The A1 notation of a range to search for a logical table of data.
                                # Values will be appended after the last row of this table.
            valueInputOption='USER_ENTERED', # How the input data should be interpreted.
            insertDataOption='INSERT_ROWS', # This ensures new rows are inserted.
            body=body
        ).execute()

        print(f"Successfully appended data. {result.get('updates').get('updatedCells')} cells updated.")
        return True
    except HttpError as err:
        print(f"Google Sheets API HTTP Error: {err.resp.status} - {err._get_reason()}")
        # More detailed error: print(err.content)
        return False
    except Exception as e:
        print(f"Error appending to Google Sheet: {e}")
        return False

if __name__ == '__main__':
    print("Running sheets_utils.py directly for testing...")
    # Ensure GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_FILE are set in your .env file or environment
    if not GOOGLE_SHEET_ID or not GOOGLE_SERVICE_ACCOUNT_FILE:
        print("Please set GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_FILE environment variables for testing.")
    else:
        print(f"Test GOOGLE_SHEET_ID: {GOOGLE_SHEET_ID}")
        print(f"Test GOOGLE_SERVICE_ACCOUNT_FILE: {GOOGLE_SERVICE_ACCOUNT_FILE}")
        sample_data = [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Test City",
            "Test Group",
            1,
            "Test User",
            "No",
            "00987654321",
            15.00,
            "Test User Pix Desc"
        ]
        if append_to_sheet(sample_data):
            print("Sample data appended successfully to Google Sheet.")
        else:
            print("Failed to append sample data to Google Sheet.") 