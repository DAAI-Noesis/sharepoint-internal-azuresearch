import azure.core.credentials
import azure.functions as func
import logging
import os
from openai import AzureOpenAI
import azure.core
import azure.search.documents
import json
# from azure.core.credentials import AzureKeyCredential
# from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery

from azure.ai.textanalytics.aio import TextAnalyticsClient
from scripts.prompting import create_prompt_from_documents

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

credential = azure.core.credentials.AzureKeyCredential(os.environ.get("AI_SEARCH_API_KEY"))
language_credential = azure.core.credentials.AzureKeyCredential(os.environ.get("LANGUAGE_API_KEY"))
search_client = azure.search.documents.SearchClient(endpoint=os.environ.get("AI_SEARCH_ENDPOINT"), index_name=os.environ.get("AI_SEARCH_INDEX"), credential=credential)

client = AzureOpenAI(
    api_version="2024-02-15-preview",
    azure_endpoint=os.environ.get("AZURE_OPENAI_API_ENDPOINT"),
)

@app.route(route="shareAI", auth_level=func.AuthLevel.ANONYMOUS)
def shareAI(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Chat trigger function')

    query = req.params.get('query')
    if not query:
        return func.HttpResponse(f"No query was received in this request. It's mandatory to ask for something.")
    else:
        #logging.info(os.environ.get("AI_SEARCH_API_KEY"))
        #logging.info(os.environ.get("AI_SEARCH_ENDPOINT"))
        #logging.info(os.environ.get("AI_SEARCH_INDEX"))
        try:
            template = """
            <|im_start|>system
            You are Noe, a helpful assistant that helps users find information on relevant documents from the company you work for, Noesis.
            You are an expert assistant trained to retrieve relevant information from a provided document or chunk. When answering questions, follow these rules strictly:

            1. **Answer Structure**: 
                - First, provide a **concise and accurate response** to the question.
                - Follow this with a **reference section** that includes the sources you used for the answer.

            2. **Reference Use**: 
                - Every piece of information in your answer must be directly tied to a **specific part** of the document or chunk used. 
                - If multiple pieces of the document contribute to the answer, provide clear citations for each one.

            3. **Answer Format**:
                - The response should be broken down into **paragraphs** if it involves multiple points.
                - Ensure **clarity** and **brevity** in your explanations. Do not add unnecessary information.

            4. **Reference Format**:
                - After providing your response, output a separate section titled "References".
                - Each reference should be on a new line, listed as:
                - Reference [X]: Include the **specific sentence(s)** or **paragraph(s)** from the chunk used in your answer.
                - Ensure that each reference ends with the corresponding URI.
                - If possible, also **summarize** the reference source for better clarity.

            5. **Example Output Format**:
                - Ensure your response looks exactly like the following example:

                ```
                ### Answer:
                [Your answer here. Be concise but detailed. Make sure you address the question directly.]

                ### References:
                - Reference [1]: [Brief reference content here—specific sentence, paragraph, or section](Reference URI: https://example.com)
                - Reference [2]: [Another brief reference content here—specific sentence, paragraph, or section](Reference URI: https://another.com)

                ```

            6. **Precision**: Always reference the **relevant context** accurately. If no appropriate reference exists for a part of the answer, explicitly state this in the reference section as:
                - **"Reference [X]: No specific reference found in the provided chunk."**

            7. **Avoid Guessing**: If you cannot confidently answer the question based on the available context, provide a polite explanation that the information is not available, and reference the closest information related to the query.

            8. **Attention to Detail**: Double-check that you are following the format exactly as specified, and that the references point to the most relevant sections of the document.

            Now, based on these instructions and the following context, respond to user queries by pulling the relevant information from the chunks provided.
            
            CONTEXT:
            {context}
            """

            vector_query = VectorizableTextQuery(text=query, k_nearest_neighbors=4, fields="summary_embedding", exhaustive=True)

            #results =  client.search(vector_queries=[vector_query], search_mode="all", query_type="full", select="*")

            results = search_client.search(
                search_text=query,  
                vector_queries= [vector_query],
                search_mode="all",
                select=["chunk", "name", "path", "last_modified", "uri","summary"],
            filter="not search.ismatch('01-Private','path')",
            top=4
            )

            context = ""
            prompt_from_docs = create_prompt_from_documents(results)
            for i,result in enumerate(results):
                context += f"Reference #{i}\n\nName:{result['name']}\nDocument Summary: {result['summary']}\n\nChunk: {result['chunk']}\nURI: {result['uri']}\n\n"
                
           
            
            prompt = template.format(context=prompt_from_docs, query=query)
            
            logging.info("----------------------------------GENERATED PROMPT--------------------------------\n\n"+prompt)

            completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {
                    "role": "user",
                    "content": query,
                },
            ],
            )
            response = completion.choices[0].message.content
            logging.info(query)
            logging.info(response)
            return func.HttpResponse(
            "{\"response\": \"" + response + "\"}",
            mimetype="application/json",
            status_code=200
        )
        except ValueError as err:
            logging.info(err)
            func.HttpResponse(
            "{\"response\": \"" + err + "\"}",
            status_code=500
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
        