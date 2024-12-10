import logging
async def get_client_info_gpt(client_name,region,industry,openai_client):
    prompt = f"""
    Refined Prompt:
    
    Retrieve publicly available information about the following client:

    Client Name: {client_name}
    Region: {region}
    Industry: {industry}
    When searching for information:

    Use the region and industry to narrow your search, as organizations may share similar names or acronyms.
    Focus on summarizing the client's primary services or products.
    Guidelines for the Response:

    Provide a concise and accurate summary of the client's offerings.
    If no information can be confidently retrieved, respond with:
    "Couldn't find information on {client_name}."
    """
    completion = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
    logging.info(f"Got completion:\n{completion}")
    response = completion.choices[0].message.content
    return response

def extract_client_name(file_path):
    """
    Extracts the 6th level from a file path, assuming the client name resides at this level.

    Args:
        file_path (str): The file path, e.g., "/drives/oid/root:/dynamic_segment/some_folder/client_name/document.docx".

    Returns:
        str: The extracted client name or None if the structure is invalid.
    """
    try:
        # Split the path into components
        parts = file_path.split("/")
        logging.info(f"Extracting client name from path: {file_path}")
        # Return the 6th component (index 5) if it exists
        if len(parts) > 5:
            return parts[6]
        else:
            logging.warning(f"Path does not contain enough components: {file_path}")
            return None
    except Exception as e:
        logging.error(f"Error extracting client name from path: {e}")
        return None
