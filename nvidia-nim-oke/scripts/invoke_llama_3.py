'''
@author jasperan

This code does the following:

    Imports the requests library.
    Defines the URL for the POST request.
    Defines the request body (payload) as a dictionary containing the model, prompt,
    max_tokens, and other hyperparameters.
    Sends a POST request using requests.post with the URL, headers, and payload as JSON.
    Otherwise, it prints an error message with the status code.
'''

from openai import OpenAI

# Define the URL (assuming that you will call the endpoint locally, but can be changed to a public IP address)
client = OpenAI(
    base_url = "http://0.0.0.0:8000/v1",
    api_key="no-key-required"
)

messages=[
    {"role":"user","content":"What is a GPU?"},
    {"role": "user", "content": "Write a short limerick about the wonders of GPU computing."}
]
 
completion = client.chat.completions.create(
    model="meta/llama3-8b-instruct",
    messages=messages,
    temperature=0.5,
    top_p=1,
    max_tokens=1024,
    stream=True)
 
for chunk in completion:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")