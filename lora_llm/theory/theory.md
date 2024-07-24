# Introduction

A significant approach in natural language processing involves pre-training large-scale models on general domain data and adapting them to specific tasks or domains. However, as we continue to increase the size of pre-trained models, fully fine-tuning all parameters becomes impractical. For instance, using GPT-3 175B as an example, deploying separate instances of fine-tuned models, each with 175B parameters, is prohibitively expensive. To address this issue, we propose a method called Low-Rank Adaptation, or LoRA.

LoRA freezes the weights of the pre-trained model and introduces trainable rank decomposition matrices into each layer of the Transformer architecture. This technique significantly reduces the number of trainable parameters required for downstream tasks. Compared to fine-tuning GPT-3 175B with Adam, LoRA can reduce the number of trainable parameters by 10,000 times and the GPU memory requirement by 3 times.

Despite having fewer trainable parameters, LoRA performs on-par with or better than fine-tuning in terms of model quality on various models such as RoBERTa, DeBERTa, GPT-2, and GPT-3. It also offers a higher training throughput and, unlike adapters, does not introduce additional inference latency. Furthermore, we conduct an empirical investigation into rank-deficiency in language model adaptation, which provides insights into the effectiveness of LoRA.

Original authors were kind enough to facilitate the integration of LoRA with some PyTorch models like ROBERTa and GPT2. Right now, a couple of months after the release of this new technique, this has expanded and LoRA is now integrated with thousands of models (most Huggingface models are supported), although most common model checkpoints come from [Alpaca](https://github.com/tatsu-lab/stanford_alpaca).

In natural language processing, numerous applications rely on adapting a single, large-scale pre-trained language model to multiple downstream tasks. Typically, this adaptation is achieved through fine-tuning, which involves updating all parameters of the pre-trained model. However, a major drawback of fine-tuning is that the resulting model ends up with the same number of parameters as the original model.

This issue becomes more critical as larger models are developed every few months. What was once merely an inconvenience for models like GPT-2 or RoBERTa large turns into a significant challenge when dealing with GPT-3, which has a staggering 175 billion trainable parameters.

To address this challenge, researchers have attempted to mitigate the problem by adapting only a subset of parameters or incorporating external modules for new tasks. By doing so, they only need to store and load a small number of task-specific parameters in addition to the pre-trained model, greatly enhancing operational efficiency during deployment. However, existing techniques.

Our hypothesis is that during the adaptation of a language model, the weight changes exhibit a low "intrinsic rank." This hypothesis forms the basis of our proposed approach called Low-Rank Adaptation (LoRA). LoRA enables us to indirectly train certain dense layers in a neural network by optimizing rank decomposition matrices for the changes in these layers, while keeping the pre-trained weights frozen. This concept is illustrated in Figure 1.

We demonstrate the effectiveness of LoRA using GPT-3 175B as an example. Our experiments show that even with a high full rank (d) of 12,288, a very low rank (r) of one or two is sufficient, making LoRA both storage- and compute-efficient.

LoRA offers several key advantages:

Sharing and reusing a pre-trained model: A single pre-trained model can be used to construct multiple small LoRA modules for different tasks. By freezing the shared model and efficiently replacing the matrices A and B in Figure 1, we can significantly reduce the storage requirement and overhead associated with task-switching.

Improved training efficiency: LoRA enhances training efficiency and lowers the hardware requirements, particularly when using adaptive optimizers. With LoRA, there is no need to compute gradients or maintain optimizer states for most parameters. Instead, we only optimize the smaller, injected low-rank matrices, resulting in up to a 3x reduction in hardware requirements.

Minimal inference latency: Our straightforward linear design allows us to merge the trainable matrices with the frozen weights during deployment. This design choice ensures that LoRA introduces no additional inference latency compared to a fully fine-tuned model.

Compatibility with other methods: LoRA is orthogonal to many existing methods and can be combined with them. For example, it can be combined with prefix-tuning. We provide an example of this combination in Appendix E.

## Conclusion
Low-Rank Adaptation of Large Language Models (LoRA) is a training method that accelerates the training of large models while consuming less memory. It adds pairs of rank-decomposition weight matrices (called update matrices) to existing weights, and only trains those newly added weights. This has a couple of advantages:

    Previous pretrained weights are kept frozen so the model is not as prone to catastrophic forgetting.
    Rank-decomposition matrices have significantly fewer parameters than the original model, which means that trained LoRA weights are easily portable.
    LoRA matrices are generally added to the attention layers of the original model. 🧨 Diffusers provides the load_attn_procs() method to load the LoRA weights into a model’s attention layers. You can control the extent to which the model is adapted toward new training images via a scale parameter.
    The greater memory-efficiency allows you to run fine-tuning on consumer GPUs like the Tesla T4, RTX 3080 or even the RTX 2080 Ti! GPUs like the T4 are free and readily accessible in Kaggle or Google Colab notebooks.