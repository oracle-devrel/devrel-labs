'''
@author jasperan

This file uses the pretrained BERT tokenizer and encoding model. It will tokenize an input phrase (replace line 15 with your own) and generate its embeddings for you to visually check them.

The output will be a tensor with shape (1, sequence_length, hidden_size), where
- sequence_length is the number of tokens in the input phrase plus special tokens (like [CLS] and [SEP])
- hidden_size is 768 for bert-base-uncased, meaning that each vector has 768 dimensions (a lot to visualize!) and the numbers represent the actual embedding values produced by BERT.

The dimensions of each vector are always (1xn) where n is a natural number (since vectors are 1-dimensional matrices), and n is determined by the embedding model you choose to use.
'''


from transformers import BertTokenizer, BertModel
import torch

# Load pre-trained BERT tokenizer and model
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')

# Tokenize input phrase
input_text = "I like my hotel room"
input_ids = tokenizer(input_text, return_tensors='pt')['input_ids']

# Get the embeddings
with torch.no_grad():
    outputs = model(input_ids)
    embeddings = outputs.last_hidden_state

# Convert embeddings to numpy array
embeddings_np = embeddings.numpy()

# Display the embeddings for the phrase
print(embeddings_np)