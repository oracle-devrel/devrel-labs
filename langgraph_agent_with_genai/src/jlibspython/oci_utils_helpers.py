import os, base64, json, mimetypes
import logging
import oci
import tempfile
import datetime
import cv2

logger = logging.getLogger(__name__)


def download_file_from_objectStore(bucket, namespace, object_name):
    try:
        config_path = os.path.expanduser("~/.oci/config")
        if os.path.exists(config_path):
            config = oci.config.from_file("~/.oci/config",profile_name=os.environ.get("OCI_CLI_PROFILE"))
            oci_client = oci.object_storage.ObjectStorageClient(config=config)
        elif os.environ.get("OCI_RESOURCE_PRINCIPAL_VERSION"):
            logger.info("Using Resource Principal for authentication")
            signer = oci.auth.signers.get_resource_principals_signer()
            oci_client = oci.object_storage.ObjectStorageClient(config={}, signer=signer)
        else:
            logger.info("Using Instance Principal for authentication")
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            oci_client = oci.object_storage.ObjectStorageClient(config={}, signer=signer)


        logger.info(f"Downloading {object_name} from OCI bucket {bucket}")

        # Create a temporary directory and construct local path with original filename
        temp_dir = tempfile.gettempdir()
        local_path = os.path.join(temp_dir, os.path.basename(object_name))

        response = oci_client.get_object(namespace, bucket, object_name)

        with open(local_path, 'wb') as f:
            for chunk in response.data.raw.stream(1024 * 1024, decode_content=False):
                f.write(chunk)

        logger.info(f"File saved to {local_path}")

        response_metadata = oci_client.head_object(namespace_name=namespace, bucket_name=bucket, object_name=object_name)

        # Extract timestamps
        last_modified_str = response_metadata.headers.get("last-modified")
        time_created_str = response_metadata.headers.get("opc-meta-timecreated")

        # Convert Last-Modified from HTTP header format to datetime
        last_modified_dt = datetime.strptime(last_modified_str, "%a, %d %b %Y %H:%M:%S %Z")

        if time_created_str:
            # If custom metadata exists for created time
            created_on_dt = datetime.fromisoformat(time_created_str)
        else:
            # Fall back to last modified if timecreated was not set
            created_on_dt = last_modified_dt

        created_on = created_on_dt.strftime("%Y-%m-%dT%H:%M:%S")
        modified_on = last_modified_dt.strftime("%Y-%m-%dT%H:%M:%S")

        return local_path, created_on, modified_on

    except Exception as e:
        logger.error(f"Failed to download file from OCI: {e}")
        raise



def extract_metadata_from_chunks_GenAI(
    chunks,
    prompt_text: str,
    ocid_compartment_id: str,
    oci_genai_endpoint: str,
    ocid_genai_model: str,
    temperature: float = 0.0,
):
    logger.info("Starting metadata extraction with LLM...")
    EMPTY_JSON = {"summary": "", "type": "", "category": "", "person": "", "eventdate": ""}

    try:
        if not prompt_text:
            return EMPTY_JSON
        config_path = os.path.expanduser("~/.oci/config")
        if os.path.exists(config_path):
            logger.info("DEBUG - Using Local config authentication in OCI")
            config = oci.config.from_file("~/.oci/config",profile_name=os.environ.get("OCI_CLI_PROFILE"))
            client = oci.generative_ai_inference.GenerativeAiInferenceClient(
                config=config,
                service_endpoint=oci_genai_endpoint,
                retry_strategy=oci.retry.NoneRetryStrategy(),
                timeout=(10, 240),
            )

        else:
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()        
            client = oci.generative_ai_inference.GenerativeAiInferenceClient(
                config={},
                signer=signer,
                service_endpoint=oci_genai_endpoint,
                retry_strategy=oci.retry.NoneRetryStrategy(),
                timeout=(10, 240),
            )

        joined = " ".join(chunks or [])
        user_prompt = f"{prompt_text}\n{joined}".strip()

        # Mensagem USER com TextContent (padrão do sample OCI)
        text_content = oci.generative_ai_inference.models.TextContent()
        text_content.text = user_prompt

        msg = oci.generative_ai_inference.models.Message()
        msg.role = "USER"
        msg.content = [text_content]

        chat_request = oci.generative_ai_inference.models.GenericChatRequest()
        chat_request.api_format = oci.generative_ai_inference.models.BaseChatRequest.API_FORMAT_GENERIC
        chat_request.messages = [msg]
        chat_request.max_tokens = 2048
        chat_request.temperature = temperature
        chat_request.frequency_penalty = 0
        chat_request.presence_penalty = 0
        chat_request.top_p = 1
        chat_request.top_k = 1

        chat_detail = oci.generative_ai_inference.models.ChatDetails()
        chat_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(model_id=ocid_genai_model)
        chat_detail.chat_request = chat_request
        chat_detail.compartment_id = ocid_compartment_id

        resp = client.chat(chat_detail)        

        logger.info("DEBUG - client.chat() executed successfully!")

        # A resposta JSON vem em choices[0].message.content[0].text
        choices = getattr(resp.data.chat_response, "choices", []) or []
        if not choices:
            return EMPTY_JSON

        msg_content = choices[0].message.content or []
        if not msg_content or not hasattr(msg_content[0], "text"):
            return EMPTY_JSON

        raw_text = (msg_content[0].text or "").strip()
        if not raw_text:
            return EMPTY_JSON

        # Tenta parsear diretamente; se falhar, remove cercas simples de markdown e tenta de novo
        try:
            return json.loads(raw_text)
        except Exception:
            cleaned = raw_text
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`").strip()
                # Se vier com "json" no início da cerca
                if cleaned.lower().startswith("json"):
                    cleaned = cleaned[4:].strip()
            try:
                return json.loads(cleaned)
            except Exception:
                return EMPTY_JSON

    except Exception as e:
        logger.error(f"Error {e}")
        return EMPTY_JSON
    

def extract_text_from_image_with_genAI(
    img_array, 
    ocid_compartment_id: str, 
    oci_genai_endpoint: str, 
    ocid_genai_model: str
) -> list[str]:
    result_text: list[str] = []
    prompt = (
        "Extract all the text from the image exactly as it appears, without any modification.\n"
        "Do not return markdown."
    )

    # converte numpy array para PNG em memória
    success, buffer = cv2.imencode(".png", img_array)
    if not success:
        return result_text

    img_bytes = buffer.tobytes()
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    config_path = os.path.expanduser("~/.oci/config")
    if os.path.exists(config_path):
        config = oci.config.from_file("~/.oci/config",profile_name=os.environ.get("OCI_CLI_PROFILE"))
        client = oci.generative_ai_inference.GenerativeAiInferenceClient(
            config=config,
            service_endpoint=oci_genai_endpoint,
            retry_strategy=oci.retry.NoneRetryStrategy(),
            timeout=(10, 240),
        )
    else:
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()    
        client = oci.generative_ai_inference.GenerativeAiInferenceClient(
            config={},
            signer=signer,
            service_endpoint=oci_genai_endpoint,
            retry_strategy=oci.retry.NoneRetryStrategy(),
            timeout=(10, 240),
        )

    text_content = oci.generative_ai_inference.models.TextContent()
    text_content.text = prompt

    image_url = oci.generative_ai_inference.models.ImageUrl(
        url=f"data:image/png;base64,{img_b64}"
    )
    image_content = oci.generative_ai_inference.models.ImageContent(image_url=image_url)

    msg = oci.generative_ai_inference.models.Message()
    msg.role = "USER"
    msg.content = [text_content, image_content]

    chat_request = oci.generative_ai_inference.models.GenericChatRequest()
    chat_request.api_format = oci.generative_ai_inference.models.BaseChatRequest.API_FORMAT_GENERIC
    chat_request.messages = [msg]
    chat_request.max_tokens = 2048
    chat_request.temperature = 0

    chat_detail = oci.generative_ai_inference.models.ChatDetails()
    chat_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(
        model_id=ocid_genai_model
    )
    chat_detail.chat_request = chat_request
    chat_detail.compartment_id = ocid_compartment_id

    try:
        resp = client.chat(chat_detail)
        choices = getattr(resp.data.chat_response, "choices", [])
        if not choices:
            return result_text

        msg_content = choices[0].message.content
        if not msg_content:
            return result_text

        raw_text = getattr(msg_content[0], "text", None)
        if not raw_text:
            return result_text

        result_text.append(raw_text.strip())
        return result_text

    except Exception as e:
        logger.error(f"Error {e}")
        return []
    

