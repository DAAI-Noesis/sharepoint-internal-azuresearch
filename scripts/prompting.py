from collections import defaultdict
import logging
import os
def create_prompt_from_documents(documents):
    # Group by document name
    doc_dict = defaultdict(list)

    for doc in documents:
        doc_dict[doc["name"]].append({
            "summary": doc["summary"],
            #"chunk": doc["chunk"],
            "uri": doc["uri"]
        })

    # Create the prompt
    prompt = ""
    for doc_name, entries in doc_dict.items():
        # Extract the summary (it's the same for all entries of the same document)
        summary = entries[0]["summary"]
        doc_uri = entries[0]["uri"]
        # Build the prompt
        prompt += f"Document Name: {doc_name}\n"
        prompt += f"Summary: {summary}\n"
        prompt += f"URI: {doc_uri}\n"

        if "chunk" in entries[0]:
            prompt += "Chunks:\n"
        
            # Add all chunks for the document
            for entry in entries:
                prompt += f"- {entry['chunk']} (URI: {entry['uri']})\n"
        
        prompt += "\n"  # New line between different documents
    
    return prompt

def generate_augmented_query(query, chat_history,openai_client):
    """
    Generate a system prompt with chat history and the user's current query.
    
    Parameters:
    - query (str): The user's current question or query.
    - chat_history (list): A list of dictionaries representing the conversation history.
                           Each dictionary should have 'role' (either 'user' or 'assistant')
                           and 'content' (the message) keys.
    
    Returns:
    - str: A formatted prompt string that includes the conversation history and the current query.
    """
    
    # Initialize the system prompt with a header or system instruction
    system_prompt,_ = load_prompt("augmented_query")
    logging.info(chat_history)
    history = ""
    # Append the chat history to the prompt, formatting each message
    for message in chat_history:
        role = "User" if message['role'] == "user" else "Assistant"
        history += f"{role}: {message['content']}\n"
    
    # Append the current user query at the end of the prompt
    prompt = system_prompt.format(conversation_context=history,user_query=query)
    
    completion = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role":"system","content":prompt}]
        )
    response = completion.choices[0].message.content
    logging.info("Augmented query: "+response)
    return response

def load_prompt(name):
    system_prompt = _load_role_prompt(name, "system")
    user_prompt = _load_role_prompt(name, "user")
    return f"""{system_prompt}""", f"""{user_prompt}"""

def _load_role_prompt(name, role):
    role_prompt_file = f"./prompts/{name}/{name}.{role}.md"
    if os.path.exists(role_prompt_file):
        with open(role_prompt_file, "r") as file:
            return file.read()
    else:
        return ""