import torch
from transformers import BertTokenizer, BertModel
import matplotlib.pyplot as plt
import numpy as np

# Load the pre-trained BERT model and tokenizer
model_name = 'bert-base-uncased'
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertModel.from_pretrained(model_name, output_attentions=True)


def get_attention_maps(text):
    # Tokenize the input text and convert it to tensor format
    inputs = tokenizer(text, return_tensors="pt")
    
    # Get the model output without computing gradients (inference mode)
    with torch.no_grad():
        outputs = model(**inputs)
    
    # Extract the attention maps from the model output
    attention_maps = outputs.attentions
    
    return attention_maps, inputs['input_ids'][0]


def visualize_attention(attention_maps, tokens, layer=0, head=0):
    # Get the attention map for the specified layer and head
    attention = attention_maps[layer][0, head].numpy()
    
    # Decode the token IDs to their corresponding string tokens
    token_labels = [tokenizer.decode([token_id]) for token_id in tokens]
    
    # Create a heatmap to visualize the attention map
    fig, ax = plt.subplots(figsize=(10, 10))
    im = ax.imshow(attention, cmap='viridis')
    
    # Set the labels for the x and y axes with the decoded tokens
    ax.set_xticks(np.arange(len(token_labels)))
    ax.set_yticks(np.arange(len(token_labels)))
    ax.set_xticklabels(token_labels)
    ax.set_yticklabels(token_labels)
    
    # Rotate the tick labels on the x-axis for better readability
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    # Add a colorbar to the heatmap to indicate the attention scores
    cbar = ax.figure.colorbar(im, ax=ax)
    
    # Set the title of the heatmap with the layer and head information
    ax.set_title(f"Attention Map (Layer {layer+1}, Head {head+1})")
    
    # Adjust the layout to fit everything nicely and display the plot
    plt.tight_layout()
    plt.show()


def visualize_attention_multi_head(attention_maps, tokens, layer=0, num_heads=4):
    # Get attention maps for specified layer and heads
    attention = attention_maps[layer][0, :num_heads].numpy()
    
    # Decode tokens
    token_labels = [tokenizer.decode([token_id]) for token_id in tokens]
    
    # Create subplots
    fig, axes = plt.subplots(2, 2, figsize=(20, 20))
    axes = axes.ravel()
    
    for i in range(num_heads):
        ax = axes[i]
        im = ax.imshow(attention[i], cmap='viridis')
        
        # Set labels
        ax.set_xticks(np.arange(len(token_labels)))
        ax.set_yticks(np.arange(len(token_labels)))
        ax.set_xticklabels(token_labels)
        ax.set_yticklabels(token_labels)
        
        # Rotate the tick labels and set their alignment
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        
        # Add colorbar
        cbar = ax.figure.colorbar(im, ax=ax)
        
        # Set title
        ax.set_title(f"Attention Map (Layer {layer+1}, Head {i+1})")
    
    plt.tight_layout()
    plt.show()


def main():
    '''
    Put your sample text here
    '''
    text = "Nacho slept on the couch last night."
    # Get the attention maps and token IDs for the sample text
    attention_maps, tokens = get_attention_maps(text)

    # You can use the below commented function to visualize the attention of a specific head and a specific layer:
    #visualize_attention(attention_maps, tokens, layer=0, head=0)
    #visualize_attention(attention_maps, tokens, layer=0, head=1)

    visualize_attention_multi_head(attention_maps, tokens, layer=0, num_heads=4)

if __name__ == '__main__':
    main()
