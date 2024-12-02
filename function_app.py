import azure.core.credentials
import azure.functions as func
import logging
import os
from openai import AzureOpenAI
import azure.core
import azure.search.documents
import json
from utils.crm_retrieval import get_region_and_industry
# from azure.core.credentials import AzureKeyCredential
# from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery

from azure.ai.textanalytics.aio import TextAnalyticsClient
from scripts.prompting import create_prompt_from_documents,load_prompt,generate_augmented_query

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

credential = azure.core.credentials.AzureKeyCredential(os.environ.get("AI_SEARCH_API_KEY"))
language_credential = azure.core.credentials.AzureKeyCredential(os.environ.get("LANGUAGE_API_KEY"))
search_client = azure.search.documents.SearchClient(endpoint=os.environ.get("AI_SEARCH_ENDPOINT"), index_name=os.environ.get("AI_SEARCH_INDEX"), credential=credential)

client = AzureOpenAI(
    api_version="2024-02-15-preview",
    azure_endpoint=os.environ.get("AZURE_OPENAI_API_ENDPOINT"),
)
@app.route(route="extract_metadata", auth_level=func.AuthLevel.ANONYMOUS)
async def extract_metadata(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Azure Search Custom Skill triggered.")

    # Parse the input JSON
    try:
        input_data = req.get_json()
    except ValueError:
        return func.HttpResponse(
            "Invalid JSON input.",
            status_code=400
        )

    # Extract parameters from input
    records = input_data.get("values", [])
    results = []

    for record in records:
        record_id = record.get("recordId")
        if not record_id:
            continue

        data = record.get("data", {})
        folder_name = data.get("folder_name")  # Folder name from the document
        opportunity_id = data.get("opportunity_id")  # Opportunity ID from the document
        document_name = data.get("document_name")
        # Call Dynamics API to retrieve region and industry
        try:
            enriched_data = get_region_and_industry(folder_name, document_name)
            logging.info("Got enriched data.")
            if enriched_data:
                results.append({
                    "recordId": record_id,
                    "data": {
                        "region": enriched_data.get("region", "Unknown"),
                        "industry": enriched_data.get("industry", "Unknown")
                    }
                })
            else:
                results.append({
                    "recordId": record_id,
                    "data": {
                        "region": None,
                        "industry": None
                    },
                    "errors": [{"message": "No matching data found in Dynamics."}]
                })
            logging.info("Extracted values:\n",enriched_data)
        except Exception as e:
            logging.error(f"Error processing record {record_id}: {e}")
            results.append({
                "recordId": record_id,
                "data": {},
                "errors": [{"message": str(e)}]
            })

    return func.HttpResponse(
        body=json.dumps({"values": results}),
        mimetype="application/json"
    )

@app.route(route="summarize", auth_level=func.AuthLevel.ANONYMOUS)
async def summarize(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Chat trigger function for summarizing text')
    input_data = req.get_json()
    logging.info("-------------------------------Input Request------------------\n"+str(input_data))
    output_records={"values":[]}
    try:
        text_analytics_client = TextAnalyticsClient(endpoint=os.environ.get("LANGUAGE_API_ENDPOINT"),credential=language_credential)

        async with text_analytics_client:

            for record in input_data.get("values",[]):
                try:
                    new_record = {"recordId":record.get("recordId")}
                    logging.info(record.get("fullText"))
                    poller = await text_analytics_client.begin_abstract_summary([record.get("data",{}).get("fullText","")],sentence_count=4)
                    abstract_summary_results = await poller.result()
                    
                    summary = [result.summaries async for result in abstract_summary_results]
                    
                    logging.info("Summary:\n"+summary[0][0].text)

                    new_record["data"]={"summary":summary[0][0].text}

                    logging.info(new_record)
                except Exception as ProcessingError:
                    logging.exception(ProcessingError)
                    err = str(ProcessingError)
                    new_record["errors"]=[{"message":err}]
                    new_record["warnings"]=""
                
                output_records["values"].append(new_record)
            logging.info("-----------------------------Output Response------------------\n"+str(output_records))
            return func.HttpResponse(
                    json.dumps(output_records,default=lambda obj: obj.__dict__),
                    mimetype="application/json",
                    status_code=200)
        
    except ValueError as err:
            logging.error(err)
            func.HttpResponse(
            "{\"response\": \"" +str(err)+ "\"}",
            status_code=500
            )


@app.route(route="ask", auth_level=func.AuthLevel.ANONYMOUS)
async def ask(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Chat trigger function')

    # Retrieve the query and chat history from request parameters
    data = req.get_json()
    query = data.get('query')
    chat_history = data.get('chat_history')

    if not query:
        return func.HttpResponse("No query was received in this request. It's mandatory to ask for something.", status_code=400)
    
    # Parse chat history from JSON if it exists
    conversation_history = []
    if chat_history:
        try:
            conversation_history = chat_history
        except json.JSONDecodeError as e:
            logging.error("Failed to decode chat history JSON")
            return func.HttpResponse("Invalid chat history format.", status_code=400)

    try:
        #Generate augmented query
        augmented_query = generate_augmented_query(query=query,chat_history=conversation_history,openai_client=client)
        logging.info("Generated Query:------------\n"+augmented_query)


        # Load the system template for the RAG prompt
        system_template, _ = load_prompt("rag")

        # Set up a vectorized query
        vector_query = VectorizableTextQuery(
            text=augmented_query,
            k_nearest_neighbors=20,
            fields="summary_embedding",
            exhaustive=True
        )

        # Execute search on the index with vector query
        results = search_client.search(
            search_text=query,  
            vector_queries=[vector_query],
            search_mode="all",
            select=["name", "path", "last_modified", "uri", "summary"],
            filter="not search.ismatch('01-Private','path')",
            top=20
        )

        # Format results into a prompt for the system message
        context = ""
        prompt_from_docs = create_prompt_from_documents(results)
        for i, result in enumerate(results):
            context += f"Reference #{i}\n\nName: {result['name']}\nDocument Summary: {result['summary']}\n\nURI: {result['uri']}\n\n"

        # Format the system prompt with document results
        system_prompt = system_template.format(context=prompt_from_docs)
        #logging.info("System prompt:\n" + system_prompt)

        # Prepare messages with chat history
        messages = [{"role": "system", "content": system_prompt}]
        for message in conversation_history:
            messages.append({"role": message["role"], "content": message["content"]})
        
        # Add the latest user query
        messages.append({"role": "user", "content": query})

        # Generate completion from the model
        completion = client.chat.completions.create(
            response_format={"type":"json_object"},
            model="gpt-4o",
            messages=messages
        )

        response = completion.choices[0].message.content
        logging.info("User Query: " + query)
        logging.info("Model Response: " + response)

        # Return the response as JSON
        return func.HttpResponse(
            response,
            mimetype="application/json",
            status_code=200
        )

    except ValueError as err:
        logging.error("Error processing request: " + str(err))
        return func.HttpResponse(
            json.dumps({"response": str(err)}),
            status_code=500
        )
