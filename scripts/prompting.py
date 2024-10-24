from collections import defaultdict

def create_prompt_from_documents(documents):
    # Group by document name
    doc_dict = defaultdict(list)

    for doc in documents:
        doc_dict[doc["name"]].append({
            "summary": doc["summary"],
            "chunk": doc["chunk"],
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
        prompt += "Chunks:\n"
        
        # Add all chunks for the document
        for entry in entries:
            prompt += f"- {entry['chunk']} (URI: {entry['uri']})\n"
        
        prompt += "\n"  # New line between different documents
    
    return prompt
