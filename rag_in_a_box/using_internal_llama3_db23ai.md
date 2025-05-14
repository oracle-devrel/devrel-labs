# AI RAG in a BOX Demo using DB23ai and Internal LLM

AI RAG in a BOX Demo using Internal LLM Engine "Ollama" could be deployed in PODMAN in your PC Mac OSX (Intel or ARM) or Windows (Intel or ARM).

This version has included 2 containers:
- Oracle Database 23ai.
- AIRAG Container.


## AI RAG in a BOX Deployment Using OLLAMA Engine in PODMAN


### **Windows** Deployment

#### Install PODMAN previously using the installer

Use the next [link](https://github.com/containers/podman/blob/main/docs/tutorials/podman-for-windows.md) to deploy PODMAN in Windows


Check tutorial for [Windows Installation](./install_win_llama3_db23ai.md).

#### Install containers 

You can deploy in Windows (Intel or ARM64) using next script [Here](./scripts/install_airagdb23ai_win.bat)


### **Mac OSX** Deployment

#### Install podman and containers 

You can deploy in Mac OSX (Intel or ARM64) using next script [Here](./scripts/install_airagdb23ai_macosx.sh)


### **Linux** Deployment

#### Install podman and containers 

You can deploy in Linux (Intel, AMD or ARM64) using next script [Here](./scripts/install_airagdb23ai_linux.sh)


### **Checking** Installation

Check if PODMAN network is correctly created:

```Code
podman network ls
```

Check if all images have been downloaded:

```Code
podman images
```

Check if containers have been started:

```Code
podman ps
```

Check if all logs of containers are OK:

```Code
podman logs -f 23aidb

podman logs -f airagdb23aiinbox
```

Connect to the database

```Code
podman exec -it 23aidb sqlplus VECDEMO/<pwd>@FREEPDB1
```



### **Troubleshooting**


Check if your 23ai Database is working for user VECDEMO (put the correct password):

```Code

podman exec -it 23aidb sqlplus VECDEMO/<pwd>@FREEPDB1

```

If you receive the next error, it means you are not able to download the HugginFace Embeddings Model:

```Code

OSError: We couldn't connect to 'https://huggingface.co' to load this file, couldn't find it in the cached files and it looks like intfloat/multilingual-e5-large is not the path to a directory containing a file named config.json. Checkout your internet connection or see how to run the library in offline mode at 'https://huggingface.co/docs/transformers/installation#offline-mode'.

raceback:

File "/usr/local/lib/python3.12/site-packages/streamlit/runtime/scriptrunner/exec_code.py", line 88, in exec_func_with_error_handling
    result = func()
             ^^^^^^
File "/usr/local/lib/python3.12/site-packages/streamlit/runtime/scriptrunner/script_runner.py", line 579, in code_to_exec
    exec(code, module.__dict__)
File "/root/llama3_Db23ai_ollama.py", line 73, in <module>
    embedding_model = HuggingFaceEmbeddings(
                      ^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/langchain_huggingface/embeddings/huggingface.py", line 59, in __init__
    self._client = sentence_transformers.SentenceTransformer(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/sentence_transformers/SentenceTransformer.py", line 320, in __init__
    modules = self._load_auto_model(
              ^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/sentence_transformers/SentenceTransformer.py", line 1528, in _load_auto_model
    transformer_model = Transformer(
                        ^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/sentence_transformers/models/Transformer.py", line 77, in __init__
    config = self._load_config(model_name_or_path, cache_dir, backend, config_args)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/sentence_transformers/models/Transformer.py", line 128, in _load_config
    return AutoConfig.from_pretrained(model_name_or_path, **config_args, cache_dir=cache_dir)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/transformers/models/auto/configuration_auto.py", line 1017, in from_pretrained
    config_dict, unused_kwargs = PretrainedConfig.get_config_dict(pretrained_model_name_or_path, **kwargs)
                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/transformers/configuration_utils.py", line 574, in get_config_dict
    config_dict, kwargs = cls._get_config_dict(pretrained_model_name_or_path, **kwargs)
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/transformers/configuration_utils.py", line 633, in _get_config_dict
    resolved_config_file = cached_file(
                           ^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/transformers/utils/hub.py", line 446, in cached_file
    raise EnvironmentError
```

You must stop and start your container

```Code

podman stop airagdb23aiinbox

podman start airagdb23aiinbox

```



## AI RAG in a BOX Deployment Using LLAMA-CPP Engine in PODMAN


