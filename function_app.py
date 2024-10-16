import azure.core.credentials
import azure.functions as func
import logging
import os
import openai
import azure.core
import azure.search.documents
import json
# from azure.core.credentials import AzureKeyCredential
# from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery

from azure.ai.textanalytics.aio import TextAnalyticsClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

openai.api_type = "azure"
openai.api_base = os.environ.get("OPENAI_API_URL")
openai.api_version = "2023-09-15-preview"
openai.api_type = "azure"
openai.api_key = os.environ.get("OPENAI_API_KEY")
credential = azure.core.credentials.AzureKeyCredential(os.environ.get("AI_SEARCH_API_KEY"))
language_credential = azure.core.credentials.AzureKeyCredential(os.environ.get("LANGUAGE_API_KEY"))
search_client = azure.search.documents.SearchClient(endpoint=os.environ.get("AI_SEARCH_ENDPOINT"), index_name=os.environ.get("AI_SEARCH_INDEX"), credential=credential)

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
            Your goal is to help users find relevant documents, given their question.
            You are given a set of the most relevant documents found in the company's database.
            Your job is to answer the users question using only the documents given to you.
            You should write the references of the documents your answers are based between <||>
                i.e. [Your answers]<|references_to_your_answers|>
            Keep your answer short but insightful.
            If you deem that the documents you've been given are not relevant, apologize and suggest some of the things you have found.
            
            Given the following document parts answer the user's Question.
            DOCUMENTS-----------\n
            {context}
            <|im_end|>
            <|im_start|>user
            Question: {query}
            <|im_end|>
            <|im_start|>assistant
            """

            vector_query = VectorizableTextQuery(text=query, k_nearest_neighbors=4, fields="embedding", exhaustive=True)

            # results =  client.search(vector_queries=[vector_query], search_mode="all", query_type="full", select="*")

            results = search_client.search(
                search_text=query,  
                vector_queries= [vector_query],
                search_mode="all",
                select=["chunk", "name", "path", "last_modified", "uri","summary"],
            filter="not search.ismatch('01-Private','path')",
            top=4
            )
 
            context = ""
            for i,result in enumerate(results):
                context += f"Document #{i}\n\nName:{result['name']}\nContent: {result['summary']}.\n\nURI: {result['uri']}\n\n"
                
            logging.info(context)

            prompt = template.format(context=context, query=query)

            response = openai.Completion.create(
                engine="gpt-35-turbo",
                prompt=prompt,
                temperature=0.5, 
                max_tokens=2048,
                n=1,
                stop=["<|im_end|>"]

            )

            print(response['choices'][0]['text'])
            logging.info(query)
            return func.HttpResponse(
            "{\"response\": \"" + response['choices'][0]['text'] + "\"}",
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
        