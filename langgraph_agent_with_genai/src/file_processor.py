import os
import logging
import numpy as np

from jlibspython.file_utils import (pdf_has_image,extract_text_from_pdf_with_PyPDF, extract_text_from_doc,extract_text_from_txt,
                                    normalize_text_list)
from jlibspython.proxy_embedding_helper import (generate_embeddings_batch)
from jlibspython.oci_utils_helpers import (extract_text_from_image_with_genAI, extract_metadata_from_chunks_GenAI)
from app_specifics import store_document_in_oracledb, file_already_exists
import datetime
from pdf2image import convert_from_path
import cv2

logger = logging.getLogger(__name__)


OCI_COMPARTMENT_ID = os.environ["OCI_COMPARTMENT_ID"]
OCI_GENAI_ENDPOINT = os.environ["OCI_GENAI_ENDPOINT"]
OCI_IMAGE_MODEL_ENDPOINT = os.environ["OCI_IMAGE_MODEL_ENDPOINT"]
OCI_GENAI_IMAGE_MODEL_OCID = os.environ["OCI_GENAI_IMAGE_MODEL_OCID"]
OCI_GENAI_REASONING_MODEL_OCID = os.environ["OCI_GENAI_REASONING_MODEL_OCID"]

## In case you decide to use a GenAI MODEL for Embedding instead of local embeedding, you must setup this variable 
if "OCI_EMBEDDING_MODEL_NAME" in os.environ:
    OCI_EMBEDDING_MODEL_NAME = os.environ["OCI_EMBEDDING_MODEL_NAME"]
else:
    OCI_EMBEDDING_MODEL_NAME = ""
## In case you decide to use a GenAI MODEL for Embedding instead of local embeedding, you must setup this variable 
if "OCI_EMBEDDING_ENDPOINT" in os.environ:
    OCI_EMBEDDING_ENDPOINT = os.environ["OCI_EMBEDDING_ENDPOINT"]
else:
    OCI_EMBEDDING_ENDPOINT = ""


ENRICH_PROMPT="""
You are an AI that extracts standardized metadata from document texts.  
The JSON fields to be returned, with examples:  
- type: try to identify the document type, based on the examples below:  
   - "voucher", "receipt", "invoice", "bill", "contract", "report", "payment_slip", "vehicle_document", "driver_license", "id_card", "taxpayer_id", "passport", "tax_form", "medical_prescription", "test_result" , "exam_request", "medical_prescription"
- category: one of the following — "PIX", "Payment Slip", "Health", "Work", "Tax", "Contract". If it doesn’t fit in any of these, set it as "Other".  
- person: the main person’s name in the document, only the most important name.  
- eventdate: in the format YYYY-MM-DD  
- summary: a brief description of the content  
- Always respond with a **valid JSON**, **without markdown** or any extra text  

Examples:  

"Transfer receipt Pix by key May 2, 2025 R$ 600.00 debited account data name JOHN taxpayer_id 111.111.111-11"  
→ {"type": "voucher", "category": "PIX", "person": "JOHN SILVA", "eventdate": "2025-05-02", "summary": "PIX transfer receipt from Itau Bank, sent by JOHN SILVA to Larissa Manuela"}  

"Receipt, received from John Almada, taxpayer_id 111.111.111-11 the amount of R$ 23.00 for physiotherapy sessions"  
→ {"type": "receipt", "category": "Health", "person": "JOHN ALMADA", "eventdate": "2025-05-02", "summary": "Payment receipt for physiotherapy sessions on 2025-05-02, covering 5 sessions"}  

"Pix completed - Date and Time: 2025-06-02 - 13:52:05 - Name: FRANCISCO SILVA"  
→ {"type": "voucher", "category": "PIX", "person": "FRANCISCO SILVA", "eventdate": "2025-06-02", "summary": "PIX transfer receipt from FRANCISCO SILVA to EDUARDO SANTOS"}  

"Medical invoice April 30, 2025 R$ 600.00 Payer JOHN SILVA Beneficiary JOHN SILVA Professional CAMILA SILVA"  
→ {"type": "invoice", "category": "Health", "person": "JOHN SILVA", "eventdate": "2025-04-30", "summary": "Medical invoice for three psychotherapy sessions in April 2025 for John Silva, issued by Camila Silva"}  

"Digital Driver License - Name: CAROLINE SILVA - ISSUE DATE: 2021-07-05"  
→ {"type": "driver_license", "category": "Document", "person": "CAROLINE SILVA", "eventdate": "2021-07-05", "summary": "Driver License issued to Caroline Silva"}  

"Tax Form - Name CAROLINE SILVA - Period: 2018-12-31"  
→ {"type": "tax_form", "category": "Tax", "person": "CAROLINE SILVA", "eventdate": "2018-12-31", "summary": "Tax Form related to the fiscal period of 2018"}  

"Exam request - Name: CAROLINE SILVA - Date: 2021-01-13"  
→ {"type": "medical_prescription", "category": "Health", "person": "CAROLINE SILVA", "eventdate": "2021-01-13", "summary": "Medical prescription with exam requests for Caroline Silva"}  

Text:
"""


def extract_text_from_pdf_Images(pdf_path):
    try:
        logger.info(f"Converting PDF to images: {pdf_path}")
        pages = convert_from_path(pdf_path)
        logger.info(f"{len(pages)} pages found")
        all_text = []

        for i, page in enumerate(pages):
            logger.info(f"Processing page {i + 1}")
            img = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
            page_text = extract_text_from_image_with_genAI(img_array=img, ocid_compartment_id=OCI_COMPARTMENT_ID,
                                                           oci_genai_endpoint=OCI_IMAGE_MODEL_ENDPOINT,
                                                           ocid_genai_model=OCI_GENAI_IMAGE_MODEL_OCID)
            all_text.extend(page_text)
        logger.info("Finished all pages")
        return all_text
    except Exception as e:
        logger.error(f"Failed to process PDF {e}")
        return []
      

def process_file_with_ocr(local_file: str):
    
    if not os.path.exists(local_file):
        logger.error(f"File not found: {local_file}")
        raise FileNotFoundError(f"{local_file} not found")

    file_ext = os.path.splitext(local_file)[1].lower()
    extracted = ""

    if file_ext == ".pdf":
        logger.info(f"Detected PDF file: {local_file}")

        extracted_text_from_image = []
        if pdf_has_image(local_file):
            logger.info(f"{local_file} has image on it, extracting text from each image...")
            extracted_text_from_image = extract_text_from_pdf_Images(local_file)

        logger.info(f"{local_file} extracting text with PyPDF")
        extracted_text = []
        extracted_text = extract_text_from_pdf_with_PyPDF(local_file)

        extracted = extracted_text + extracted_text_from_image

    elif file_ext in [".jpg", ".jpeg", ".png"]:
        logger.info(f"Detected image file: {local_file}")
        logger.info("Opening image")
        img = cv2.imread(local_file)
        extracted = extract_text_from_image_with_genAI(img_array=img, ocid_compartment_id=OCI_COMPARTMENT_ID,
                                                           oci_genai_endpoint=OCI_IMAGE_MODEL_ENDPOINT,
                                                           ocid_genai_model=OCI_GENAI_IMAGE_MODEL_OCID)
        #logger.info(f"Extracted text from image is {extracted} ")

    elif file_ext in [".doc", ".docx"]:
        logger.info(f"Detected Word document: {local_file}")
        extracted = extract_text_from_doc(local_file)

    elif file_ext == ".txt":
        logger.info(f"Detected TXT file: {local_file}")
        extracted = extract_text_from_txt(local_file)

    else:
        logger.error("Unsupported file type. Only PDF, JPG, JPEG, PNG, DOC, DOCX, or TXT are supported.")
        raise ValueError(f"Unsupported file type: {file_ext}")

    return normalize_text_list(extracted)


def processFile(source_file_path:str, created_on:datetime, modified_on:datetime ):

    # Check if file is already indexed
    if file_already_exists(source_file_path):
        return {"status": "skipped", "reason": "File already exists in database"}

    try:
        logger.info(f"Extract text chunks from file [{source_file_path}]...")
        chunks = process_file_with_ocr(source_file_path)
    except Exception as e:
        return {"status": "failed", "reason": f"Text extraction error: {str(e)}"}

    try:
        if chunks:
            logger.info("Detected chunks from text")
            for attempt in range(3):
                logger.info(f"Capture metadata using LLM [attempt {attempt + 1}/3] - model {OCI_GENAI_REASONING_MODEL_OCID}")
                metadata = extract_metadata_from_chunks_GenAI(chunks=chunks,prompt_text=ENRICH_PROMPT, ocid_compartment_id=OCI_COMPARTMENT_ID,
                                                              ocid_genai_model=OCI_GENAI_REASONING_MODEL_OCID, oci_genai_endpoint=OCI_GENAI_ENDPOINT)            
                if metadata.get("summary") and metadata.get("type"):
                    logger.info("LLM completed!")
                    break
                else:
                    logger.info(f"Metada output is {metadata}")
                    return {"status": "failed", "reason": "Failed to extract metadata after 3 attempts"}
            
    except Exception as e:
        return {"status": "failed", "reason": f"Metadata enrichment error: {str(e)}"}

    if not chunks:
        return {"status": "failed", "reason": "No text extracted from file."}

    # Save all chunkgs into a single CLOB column on DB
    file_name = os.path.basename(source_file_path)
    merged_clob_chunks = file_name + "\n" + "\n".join(chunks)

    try:
        logger.info(f"Starting embedding extracted data...")
        embeddings = generate_embeddings_batch(chunks,compartment_id=OCI_COMPARTMENT_ID, embedding_model=OCI_EMBEDDING_MODEL_NAME, genai_endpoint=OCI_EMBEDDING_ENDPOINT)
        logger.info(f"Finished embedding!")
    except Exception as e:
        return {"status": "failed", "reason": f"Embedding generation failed: {str(e)}"}
    
    
    result = store_document_in_oracledb(source_file_path, merged_clob_chunks, embeddings, metadata, created_on, modified_on, 
                                        compartment_id=OCI_COMPARTMENT_ID,embedding_model=OCI_EMBEDDING_MODEL_NAME, genai_endpoint=OCI_EMBEDDING_ENDPOINT)
    return result





