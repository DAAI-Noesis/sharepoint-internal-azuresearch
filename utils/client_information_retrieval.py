
async def get_client_info_gpt(client_name,openai_client):
    prompt = f"""
    Retrieve publicly available information about {client_name}, such as:
    - Industry
    - Location
    - Key Services
    Your answer should be a summary of what you found.
    """
    completion = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
    response = completion.choices[0].message.content
    return response