import requests
import urllib
import msal
import os
import logging
import re

def get_region_and_industry(folder_name, document_name):
    """
    Queries the Dynamics API to get region and industry based on folder name and document name.

    Args:
        folder_name (str): Folder name (relativeurl).
        document_name (str): Document name.

    Returns:
        dict: A dictionary with "region" and "industry".
    """
    TOKEN = acquire_token() # Replace with dynamic token retrieval for production
    URL =  os.environ.get("TOKEN_RETRIEVAL_URL")
    logging.info(f"Getting region and industry for {folder_name}, document {document_name}")
    if document_name:
        sapid,opportunity_id,account_number  = extract_ids_from_file_name(document_name)
    else:
        sapid,opportunity_id = "None"

    # FetchXML Template
    fetchXmlTemplate = """<fetch>
<entity name="account">
<attribute name="accountid" />
<attribute name="name" />
<attribute name="noesis_industry" />
<attribute name="noesis_country" />
<filter type="or">
<condition attribute="name" operator="eq" value="{folder_name}"/>
<condition attribute="accountnumber" operator="eq" value="{account_number}" />
<condition entityname="OPPORTUNITY" attribute="new_sapid" operator="eq" value="{sapid}" />
<condition entityname="OPPORTUNITY" attribute="new_oportunidade" operator="eq" value="{opportunity_id}" />
</filter>
<link-entity name="opportunity" from="customerid" to="accountid" alias="OPPORTUNITY">
<attribute name="new_sapid" />
<attribute name="new_oportunidade" />
<attribute name="opportunityid" />
<filter type="or">
<!--<condition attribute="new_sapid" operator="eq" value="BCTT-0N005" />-->
<!--<condition attribute="modifiedon" operator="last-x-years" value="1" />-->
<!--<condition attribute="createdon" operator="last-x-years" value="1" />-->
</filter>
</link-entity>
</entity>
</fetch>

"""

    # Populate the FetchXML with parameters
    fetchXml = fetchXmlTemplate.format(
        folder_name=folder_name,
        account_number=account_number,
        sapid=sapid,
        opportunity_id=opportunity_id
    )
    logging.info(fetchXml)

    encoded_fetchXml = urllib.parse.quote(fetchXml)

    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Prefer": "odata.include-annotations=*"
    }

    # Make the API request
    response = requests.get(URL, headers=headers, params={"fetchXml": encoded_fetchXml})
    if response.status_code != 200:
        raise Exception(f"API request failed with status {response.status_code}: {response.text}")
    logging.info(response.json()["value"])
    # Parse the JSON response
    results = response.json()["value"]
    if results:
        item = results[0]  # We only need the first match
        answer = {
            "region": item.get("_noesis_country_value@OData.Community.Display.V1.FormattedValue", "Unknown"),
            "industry": item.get("_noesis_industry_value@OData.Community.Display.V1.FormattedValue", "Unknown"),
            "client_name": item.get("name", "Unknown")
        }
        logging.info(f"Found {answer['client_name']}\n Industry:{answer['industry']}\nRegion{answer['region']}")
        return answer
    
    return None

def acquire_token():
    """
    Acquires an access token from Microsoft Entra (formerly Azure AD) using MSAL.

    Returns:
        str: A valid access token.
    Raises:
        Exception: If token acquisition fails after retries.
    """
    try:
        # Initialize MSAL Confidential Client
        client_app = msal.ConfidentialClientApplication(
            os.environ.get('CLIENT_ID'),
            authority=os.environ.get('AUTHORITY'),
            client_credential=os.environ.get('CLIENT_SECRET')
        )

        # Define the scopes
        scope = os.environ.get("SCOPE")

        # Retry logic
        retries = 3
        for attempt in range(retries):
            try:
                # Attempt to acquire the token
                authentication = client_app.acquire_token_for_client(scopes=[scope])

                if "access_token" in authentication:
                    logging.info(f"Token acquired successfully on attempt {attempt + 1}.")
                    return authentication["access_token"]
                else:
                    logging.warning(f"Attempt {attempt + 1} failed: {authentication.get('error_description', 'No details provided')}")

            except Exception as e:
                logging.error(f"Attempt {attempt + 1} encountered an error: {e}")

            # Wait briefly before retrying
            if attempt < retries - 1:
                import time
                time.sleep(2)  # Sleep for 2 seconds before retrying

        # If all retries fail, raise an exception
        raise Exception("Failed to acquire access token after multiple attempts.")
    
    except Exception as e:
        logging.critical(f"Critical failure in token acquisition: {e}")
        raise

# Extract the code from the filename
def extract_ids_from_file_name(file_name):
    """
    Extracts SAP ID and Opportunity ID from the file name.

    Args:
        file_name (str): The file name to parse.

    Returns:
        tuple: (sapid, opportunity_id)
    """
    # Regex patterns for SAP ID and Opportunity ID
    logging.info(f"Extracting Ids from {file_name}")
    sapid_pattern = r"([A-Z0-9]{4}-[A-Z0-9]{5})"  # SAP ID format
    opportunity_id_pattern = r"([A-Z0-9]{4}-[A-Z0-9]{5}-[A-Z0-9]{3})"  # Opportunity ID format

    # Extract Opportunity ID
    opportunity_id = None
    match = re.search(opportunity_id_pattern, file_name)
    if match:
        opportunity_id = match.group(1)
    else:
        opportunity_id = "OppID Not Found"

    # Extract SAP ID (falls back to the shorter version if Opportunity ID is not found)
    sapid = None
    account_number=None
    match = re.search(sapid_pattern, file_name)
    if match:
        sapid = match.group(1)
        account_number=sapid.split("-")[0]
    else:
        "SapID not found."
    logging.info(f"Extracted Information \nAccountID:{account_number}SapID : {sapid}\nExtracted opportunity ID: {opportunity_id}------")
    return sapid, opportunity_id,account_number


def extract_client_name(file_path):
    # Split the path into components
    parts = file_path.split("/")
    
    # Check if the path has enough components and extract the client name
    if len(parts) > 4:
        client_name = parts[4]  # The 5th component (index 4) contains the client name
        return client_name
    else:
        return None  # Path format is invalid or doesn't contain enough components