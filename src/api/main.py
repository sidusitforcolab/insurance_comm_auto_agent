"""FastAPI application for insurance underwriting agent."""
import logging
import os
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from mangum import Mangum
from pydantic import BaseModel, Field, field_validator, model_validator

from src.agent.graph import InsuranceUnderwritingAgent
from src.config.settings import settings
from src.observability.prometheus_metrics import API_ERRORS, UNDERWRITING_REQUESTS, setup_metrics
from src.retrieval.embeddings import EmbeddingClient
from src.retrieval.pdf_parser import process_pdf_for_embedding
from src.retrieval.pgvector_client import PGVectorClient

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Commercial Auto Insurance Underwriting Agent",
    description="AI-powered underwriting for commercial auto insurance",
    version="1.0.0"
)

if settings.prometheus_enabled:
    setup_metrics(app)

# Initialize components
agent = InsuranceUnderwritingAgent()
pg_client = PGVectorClient()
embedding_client = EmbeddingClient()


class UnderwritingRequest(BaseModel):
    """Request model for underwriting."""
    applicant_id: str
    company_name: Optional[str] = None
    business_age: Optional[int] = Field(default=None, ge=0, le=100)
    number_of_vehicles: Optional[int] = Field(default=None, gt=0)
    vehicle_types: Optional[list[str]] = Field(default_factory=list)
    previous_claims: Optional[int] = Field(default=0, ge=0)
    serious_accidents: Optional[int] = Field(default=0, ge=0)
    safety_program: bool = Field(default=False)
    annual_mileage: Optional[int] = Field(default=None, gt=0)

    @field_validator("applicant_id")
    def validate_applicant_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Applicant ID must not be empty")
        trimmed = value.strip()
        if len(trimmed) < 3:
            raise ValueError("Applicant ID must be at least 3 characters")
        return trimmed

    @field_validator("company_name")
    def validate_company_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if normalized and len(normalized) < 3:
            raise ValueError("Company name must be at least 3 characters")
        return normalized

    @field_validator("vehicle_types")
    def validate_vehicle_types(cls, value: Optional[list[str]]) -> list[str]:
        if value is None:
            return []

        allowed = {"sedan", "truck", "van", "bus", "fleet", "suv", "motorcycle"}
        normalized = [vehicle.strip().lower() for vehicle in value if vehicle and vehicle.strip()]
        if not normalized:
            raise ValueError("At least one vehicle type is required for commercial auto underwriting")

        invalid = [vehicle for vehicle in normalized if vehicle not in allowed]
        if invalid:
            raise ValueError(
                f"Unsupported vehicle type(s): {invalid}. Allowed types: {sorted(allowed)}"
            )
        return normalized

    @model_validator(mode="after")
    def validate_claims_and_fleet(cls, model):
        if model.serious_accidents is not None and model.previous_claims is not None:
            if model.serious_accidents > model.previous_claims:
                raise ValueError("Serious accidents cannot exceed total previous claims")

        if model.vehicle_types and model.number_of_vehicles is None:
            raise ValueError("Number of vehicles is required when vehicle types are provided")

        return model


class UnderwritingResponse(BaseModel):
    """Response model for underwriting."""
    applicant_id: str
    decision: str
    premium: Optional[float] = None
    reasoning: str
    cached: bool = False
    errors: list = []


@app.post("/underwrite", response_model=UnderwritingResponse)
async def underwrite_application(request: UnderwritingRequest):
    """Process an underwriting request."""
    try:
        logger.info(f"Processing underwriting request for applicant {request.applicant_id}")

        # Validate request
        if not request.applicant_id:
            raise HTTPException(status_code=400, detail="Applicant ID is required")

        # Process underwriting
        result = agent.process_underwriting(
            applicant_id=request.applicant_id,
            company_name=request.company_name,
            business_age=request.business_age,
            number_of_vehicles=request.number_of_vehicles,
            vehicle_types=request.vehicle_types,
            previous_claims=request.previous_claims,
            serious_accidents=request.serious_accidents,
            safety_program=request.safety_program,
            annual_mileage=request.annual_mileage
        )

        if result.get("decision"):
            UNDERWRITING_REQUESTS.labels(decision=result["decision"]).inc()

        return UnderwritingResponse(**result)

    except HTTPException as http_exc:
        API_ERRORS.labels(endpoint="/underwrite", status_code=str(http_exc.status_code)).inc()
        raise
    except Exception as e:
        API_ERRORS.labels(endpoint="/underwrite", status_code="500").inc()
        logger.error(f"Underwriting request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Underwriting failed: {str(e)}")


@app.post("/ingest-document")
async def ingest_document(
    applicant_id: str,
    document_type: str,
    file: UploadFile = File(...)
):
    """Ingest and process a document for an applicant."""
    try:
        logger.info(f"Ingesting document for applicant {applicant_id}, type: {document_type}")

        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # Validate file size
        file_content = await file.read()
        if len(file_content) > settings.max_file_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
            )

        # Save file temporarily for processing
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(file_content)

        try:
            # Process PDF
            full_text, chunks, structured_data = process_pdf_for_embedding(
                temp_path, document_type
            )

            # Store document metadata
            document_id = pg_client.store_document(
                file.filename, document_type, applicant_id, full_text
            )

            # Generate embeddings for chunks
            embeddings = embedding_client.generate_embeddings(chunks)

            # Store embeddings in pgvector
            pg_client.store_embeddings(document_id, chunks, embeddings)

            logger.info(f"Document ingested successfully: {file.filename}")

            return {
                "status": "success",
                "document_id": document_id,
                "filename": file.filename,
                "document_type": document_type,
                "applicant_id": applicant_id,
                "chunks_processed": len(chunks),
                "embeddings_stored": len(embeddings),
                "structured_data": structured_data
            }

        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except HTTPException:
        API_ERRORS.labels(endpoint="/ingest-document", status_code="400").inc()
        raise
    except Exception as e:
        API_ERRORS.labels(endpoint="/ingest-document", status_code="500").inc()
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Document ingestion failed: {str(e)}")


@app.get("/decision/{applicant_id}")
async def get_decision(applicant_id: str):
    """Get cached underwriting decision for an applicant."""
    try:
        logger.info(f"Retrieving decision for applicant {applicant_id}")

        result = pg_client.get_underwriting_decision(applicant_id)

        if not result:
            raise HTTPException(status_code=404, detail="No decision found for applicant")

        return {
            "applicant_id": applicant_id,
            "decision": result["decision"],
            "premium": result["premium_amount"],
            "reasoning": result["reasoning"],
            "created_at": result["created_at"]
        }

    except HTTPException:
        API_ERRORS.labels(endpoint="/decision", status_code="404").inc()
        raise
    except Exception as e:
        API_ERRORS.labels(endpoint="/decision", status_code="500").inc()
        logger.error(f"Failed to retrieve decision: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve decision: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        db_healthy = pg_client.health_check()

        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "version": "1.0.0"
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Lambda handler
handler = Mangum(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)