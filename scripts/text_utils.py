import re
import logging

def extract_answer_and_references(llm_response,search_responses):
    """
    Extracts the response and references from a formatted text.

    Parameters:
        llm_response (str): The formatted llm answer and references.

    Returns:
        dict: A JSON-like dictionary containing:
            - "response" (str): The main answer.
            - "references" (list): A list of references, where each reference is a dictionary with:
                - "reference_id" (str): The reference identifier (e.g., "Reference [1]").
                - "short_sentence" (str): The short sentence or content of the reference.
    """
    # Split the formatted text by sections
    sections = re.split(r'### Answer:|### References:', llm_response)
    
    # Extract the main answer (strip any extra newlines or spaces)
    answer = sections[1].strip() if len(sections) > 1 else ""
    
    # Extract the references block (if available)
    references_text = sections[2].strip() if len(sections) > 2 else ""
    
    # Extract each reference line
    references = []
    for line in references_text.splitlines():
        logging.info(line)
        match = re.match(r'- Reference \[#(\d+)\]: "(.*?)"', line)
        if match:
            print(match)
            reference_id = match.group(1)
            reference_uri = search_responses[int(reference_id)]["uri"]
            short_sentence = match.group(2)
            references.append({"reference_id": reference_id,"reference_uri": reference_uri, "short_sentence": short_sentence})
    
    # Return the extracted data as a dictionary
    return {
        "response": answer,
        "references": references
    }
