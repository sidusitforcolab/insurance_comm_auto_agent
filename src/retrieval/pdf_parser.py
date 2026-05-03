"""PDF text extraction and chunking utilities."""
import re
from typing import List, Tuple

from PyPDF2 import PdfReader


class PDFParser:
    """Parse and extract text from PDF documents."""

    def __init__(self):
        """Initialize the PDF parser."""
        pass

    def extract_text(self, file_path: str) -> str:
        """Extract all text from a PDF file."""
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF {file_path}: {str(e)}")

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for embedding."""
        if not text:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # If we're not at the end, try to break at a sentence or word boundary
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                sentence_end = text.rfind('.', end - 100, end)
                if sentence_end > start + chunk_size // 2:
                    end = sentence_end + 1
                else:
                    # Look for word boundaries
                    space_pos = text.rfind(' ', end - 50, end)
                    if space_pos > start + chunk_size // 2:
                        end = space_pos

            chunk = text[start:end].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)

            # Move start position with overlap
            start = end - overlap

            # Ensure we don't get stuck
            if start >= len(text) or len(chunk) < 50:
                break

        return chunks

    def extract_structured_data(self, text: str, document_type: str) -> dict:
        """Extract structured data based on document type."""
        if document_type == "mvr":
            return self._extract_mvr_data(text)
        elif document_type == "loss_run":
            return self._extract_loss_run_data(text)
        elif document_type == "inspection":
            return self._extract_inspection_data(text)
        elif document_type == "policy":
            return self._extract_policy_data(text)
        else:
            return {"raw_text": text}

    def _extract_mvr_data(self, text: str) -> dict:
        """Extract structured data from Motor Vehicle Record."""
        data = {}

        # Extract driver information
        name_match = re.search(r'Name:\s*([^\n]+)', text, re.IGNORECASE)
        if name_match:
            data['driver_name'] = name_match.group(1).strip()

        license_match = re.search(r'License Number:\s*([^\n]+)', text, re.IGNORECASE)
        if license_match:
            data['license_number'] = license_match.group(1).strip()

        dob_match = re.search(r'Date of Birth:\s*([^\n]+)', text, re.IGNORECASE)
        if dob_match:
            data['date_of_birth'] = dob_match.group(1).strip()

        # Extract vehicle information
        make_model_match = re.search(r'Make/Model:\s*([^\n]+)', text, re.IGNORECASE)
        if make_model_match:
            data['vehicle_make_model'] = make_model_match.group(1).strip()

        year_match = re.search(r'Year:\s*([^\n]+)', text, re.IGNORECASE)
        if year_match:
            data['vehicle_year'] = year_match.group(1).strip()

        vin_match = re.search(r'VIN:\s*([^\n]+)', text, re.IGNORECASE)
        if vin_match:
            data['vin'] = vin_match.group(1).strip()

        # Extract violations
        violations = []
        # Look for violation table data
        violation_pattern = r'(\d{4}-\d{2}-\d{2})\s+([^\d]+)\s+(\d+)\s+\$(\d+)'
        matches = re.findall(violation_pattern, text)
        for match in matches:
            violations.append({
                'date': match[0],
                'description': match[1].strip(),
                'points': int(match[2]),
                'fine': float(match[3])
            })

        data['violations'] = violations
        data['violation_count'] = len(violations)

        return data

    def _extract_loss_run_data(self, text: str) -> dict:
        """Extract structured data from Loss Run report."""
        data = {}

        # Extract company information
        company_match = re.search(r'Company Name:\s*([^\n]+)', text, re.IGNORECASE)
        if company_match:
            data['company_name'] = company_match.group(1).strip()

        # Extract claims
        claims = []
        # Look for claim table data
        claim_pattern = r'(\d{4}-\d{2}-\d{2})\s+(CLM\d+)\s+\$([\d,]+\.?\d*)\s+([^\n]+)'
        matches = re.findall(claim_pattern, text)
        total_loss = 0
        for match in matches:
            amount = float(match[2].replace(',', ''))
            claims.append({
                'date': match[0],
                'claim_number': match[1],
                'amount': amount,
                'description': match[3].strip()
            })
            total_loss += amount

        data['claims'] = claims
        data['claim_count'] = len(claims)
        data['total_loss_amount'] = total_loss

        return data

    def _extract_inspection_data(self, text: str) -> dict:
        """Extract structured data from Inspection Report."""
        data = {}

        # Extract inspection rating
        rating_match = re.search(r'Overall Rating:\s*([^\n]+)', text, re.IGNORECASE)
        if rating_match:
            data['overall_rating'] = rating_match.group(1).strip()

        # Count passed/failed items
        pass_count = len(re.findall(r'\bPASS\b', text))
        fail_count = len(re.findall(r'\bFAIL\b', text))

        data['passed_items'] = pass_count
        data['failed_items'] = fail_count
        data['total_items'] = pass_count + fail_count

        # Determine if inspection passed
        data['inspection_passed'] = fail_count == 0

        return data

    def _extract_policy_data(self, text: str) -> dict:
        """Extract structured data from Policy Document."""
        data = {}

        # Extract policy information
        policy_match = re.search(r'Policy Number:\s*([^\n]+)', text, re.IGNORECASE)
        if policy_match:
            data['policy_number'] = policy_match.group(1).strip()

        effective_match = re.search(r'Effective Date:\s*([^\n]+)', text, re.IGNORECASE)
        if effective_match:
            data['effective_date'] = effective_match.group(1).strip()

        # Extract coverage limits (simplified)
        liability_match = re.search(r'Bodily Injury Liability.*?\$([^\s]+)', text, re.IGNORECASE)
        if liability_match:
            data['liability_limit'] = liability_match.group(1)

        return data


def process_pdf_for_embedding(file_path: str, document_type: str) -> Tuple[str, List[str], dict]:
    """Process a PDF file and return text, chunks, and structured data."""
    parser = PDFParser()

    # Extract full text
    full_text = parser.extract_text(file_path)

    # Create chunks for embedding
    chunks = parser.chunk_text(full_text)

    # Extract structured data
    structured_data = parser.extract_structured_data(full_text, document_type)

    return full_text, chunks, structured_data