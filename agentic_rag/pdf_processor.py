from pathlib import Path
from typing import List, Dict, Any
import json
import argparse
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from urllib.parse import urlparse
import warnings
import transformers
import uuid  # Add at the top with other imports

# Suppress the token length warning
warnings.filterwarnings('ignore', category=UserWarning, module='transformers.generation.utils')

def is_url(string: str) -> bool:
    """Check if a string is a valid URL"""
    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except:
        return False

class PDFProcessor:
    def __init__(self, tokenizer: str = "BAAI/bge-small-en-v1.5"):
        """Initialize PDF processor with Docling components"""
        # Suppress CUDA compilation warnings
        warnings.filterwarnings('ignore', category=UserWarning, module='torch.utils.cpp_extension')
        # Suppress token length warnings
        warnings.filterwarnings('ignore', category=UserWarning, module='transformers.generation.utils')
        warnings.filterwarnings('ignore', category=UserWarning, module='transformers.modeling_utils')
        
        self.converter = DocumentConverter()
        self.tokenizer = tokenizer
    
    def _extract_metadata(self, meta: Any) -> Dict[str, Any]:
        """Safely extract metadata from various object types"""
        try:
            if hasattr(meta, '__dict__'):
                # If it's an object with attributes
                return {
                    "headings": getattr(meta, "headings", []),
                    "page_numbers": self._extract_page_numbers(meta)
                }
            elif isinstance(meta, dict):
                # If it's a dictionary
                return {
                    "headings": meta.get("headings", []),
                    "page_numbers": self._extract_page_numbers(meta)
                }
            else:
                # Default empty metadata
                return {
                    "headings": [],
                    "page_numbers": []
                }
        except Exception as e:
            print(f"Warning: Error extracting metadata: {str(e)}")
            return {
                "headings": [],
                "page_numbers": []
            }
    
    def _try_chunk_with_size(self, document: Any, chunk_size: int) -> List[Any]:
        """Try chunking with a specific size, return None if it fails"""
        try:
            # Create a new chunker with the specified size
            chunker = HybridChunker(
                tokenizer=self.tokenizer,
                chunk_size=chunk_size,
                chunk_overlap=0.1
            )
            return list(chunker.chunk(document))
        except Exception as e:
            print(f"Warning: Chunking failed with size {chunk_size}: {str(e)}")
            return None

    def process_pdf(self, file_path: str | Path) -> List[Dict[str, Any]]:
        """Process a PDF file and return chunks of text with metadata"""
        try:
            # Generate a unique document ID
            document_id = str(uuid.uuid4())
            
            # Convert PDF using Docling
            conv_result = self.converter.convert(file_path)
            if not conv_result or not conv_result.document:
                raise ValueError(f"Failed to convert PDF: {file_path}")
            
            # Try chunking with progressively smaller sizes
            chunks = None
            for chunk_size in [200, 150, 100, 75]:
                chunks = self._try_chunk_with_size(conv_result.document, chunk_size)
                if chunks:
                    print(f"Successfully chunked with size {chunk_size}")
                    break
            
            if not chunks:
                raise ValueError("Failed to chunk document with any chunk size")
            
            # Process chunks into a standardized format
            processed_chunks = []
            for chunk in chunks:
                # Handle both dictionary and DocChunk objects
                text = chunk.text if hasattr(chunk, 'text') else chunk.get('text', '')
                meta = chunk.meta if hasattr(chunk, 'meta') else chunk.get('meta', {})
                
                metadata = self._extract_metadata(meta)
                metadata["source"] = str(file_path)
                metadata["document_id"] = document_id  # Add document_id to metadata
                
                processed_chunk = {
                    "text": text,
                    "metadata": metadata
                }
                processed_chunks.append(processed_chunk)
            
            return processed_chunks, document_id  # Return both chunks and document_id
        
        except Exception as e:
            raise Exception(f"Error processing PDF {file_path}: {str(e)}")

    def process_pdf_url(self, url: str) -> List[Dict[str, Any]]:
        """Process a PDF file from a URL and return chunks of text with metadata"""
        try:
            # Convert PDF using Docling's built-in URL support
            conv_result = self.converter.convert(url)
            if not conv_result or not conv_result.document:
                raise ValueError(f"Failed to convert PDF from URL: {url}")
            
            # Generate a unique document ID
            document_id = str(uuid.uuid4())
            
            # Chunk the document
            chunks = list(self.chunker.chunk(conv_result.document))
            
            # Process chunks into a standardized format
            processed_chunks = []
            for chunk in chunks:
                # Handle both dictionary and DocChunk objects
                text = chunk.text if hasattr(chunk, 'text') else chunk.get('text', '')
                meta = chunk.meta if hasattr(chunk, 'meta') else chunk.get('meta', {})
                
                metadata = self._extract_metadata(meta)
                metadata["source"] = url
                metadata["document_id"] = document_id
                
                processed_chunk = {
                    "text": text,
                    "metadata": metadata
                }
                processed_chunks.append(processed_chunk)
            
            return processed_chunks, document_id
        
        except Exception as e:
            raise Exception(f"Error processing PDF from URL {url}: {str(e)}")
    
    def process_directory(self, directory: str | Path) -> List[Dict[str, Any]]:
        """Process all PDF files in a directory"""
        directory = Path(directory)
        all_chunks = []
        document_ids = []
        
        for pdf_file in directory.glob("**/*.pdf"):
            try:
                chunks, doc_id = self.process_pdf(pdf_file)
                all_chunks.extend(chunks)
                document_ids.append(doc_id)
                print(f"✓ Processed {pdf_file} (ID: {doc_id})")
            except Exception as e:
                print(f"✗ Failed to process {pdf_file}: {str(e)}")
        
        return all_chunks, document_ids
    
    def _extract_page_numbers(self, meta: Any) -> List[int]:
        """Extract page numbers from chunk metadata"""
        page_numbers = set()
        try:
            if hasattr(meta, 'doc_items'):
                items = meta.doc_items
            elif isinstance(meta, dict) and 'doc_items' in meta:
                items = meta['doc_items']
            else:
                return []
            
            for item in items:
                if hasattr(item, 'prov'):
                    provs = item.prov
                elif isinstance(item, dict) and 'prov' in item:
                    provs = item['prov']
                else:
                    continue
                
                for prov in provs:
                    if hasattr(prov, 'page_no'):
                        page_numbers.add(prov.page_no)
                    elif isinstance(prov, dict) and 'page_no' in prov:
                        page_numbers.add(prov['page_no'])
            
            return sorted(list(page_numbers))
        except Exception as e:
            print(f"Warning: Error extracting page numbers: {str(e)}")
            return []

def main():
    parser = argparse.ArgumentParser(description="Process PDF files and extract text chunks")
    parser.add_argument("--input", required=True, 
                       help="Input PDF file, directory, or URL (http/https URLs supported)")
    parser.add_argument("--output", required=True, help="Output JSON file for chunks")
    parser.add_argument("--tokenizer", default="BAAI/bge-small-en-v1.5", help="Tokenizer to use for chunking")
    
    args = parser.parse_args()
    processor = PDFProcessor(tokenizer=args.tokenizer)
    
    try:
        # Create output directory if it doesn't exist
        output_dir = Path(args.output).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if is_url(args.input):
            print(f"\nProcessing PDF from URL: {args.input}")
            print("=" * 50)
            chunks, doc_id = processor.process_pdf_url(args.input)
            print(f"Document ID: {doc_id}")
        elif Path(args.input).is_dir():
            print(f"\nProcessing directory: {args.input}")
            print("=" * 50)
            chunks, doc_ids = processor.process_directory(args.input)
            print(f"Document IDs: {', '.join(doc_ids)}")
        else:
            print(f"\nProcessing file: {args.input}")
            print("=" * 50)
            chunks, doc_id = processor.process_pdf(args.input)
            print(f"Document ID: {doc_id}")
        
        # Save chunks to JSON
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        
        print("\nSummary:")
        print(f"✓ Processed {len(chunks)} chunks")
        print(f"✓ Saved to {args.output}")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main() 