# Commercial Auto Insurance Underwriting Agent

An AI-powered agent for commercial auto insurance underwriting using LangGraph, PostgreSQL+pgvector, and serverless AWS Lambda deployment.

## Features

- **Document Processing**: Ingest and analyze MVR, loss run, inspection reports, and policy documents
- **Risk Assessment**: Rules-based + LLM reasoning for premium calculation
- **Web Search Integration**: Bing search for company background and risk indicators
- **Vector Search**: PostgreSQL + pgvector and optional Pinecone retrieval
- **Security**: Llama Guard input validation and AWS WAF guidance
- **Deployment Options**: AWS Lambda or EKS + FastAPI
- **Model Hosting**: Optional AWS SageMaker inference integration
- **Observability**: Prometheus metrics, LangSmith tracing, Arize Phoenix, Ragas quality scoring

## Tool Integration

This project includes integration points for the following tools:

- **LangGraph** for workflow orchestration
- **AWS EKS** for Kubernetes / FastAPI deployment patterns
- **AWS SageMaker** for model hosting and inference
- **AWS WAF** for web application firewall recommendations
- **Pinecone** for optional vector storage and search
- **Aurora/PostgreSQL + pgvector** for vector DB persistence
- **Bing** and **Tawily** for external business and risk data enrichment
- **LangSmith** for execution tracing
- **Ragas** for RAG quality assessment
- **Arize Phoenix** for production monitoring and event logging
- **Prometheus + Grafana** for metrics collection and visualization

## Architecture

```
PDF Upload → LangGraph Workflow → Premium Decision
    ↓              ↓
Vector Store    Web Search
    ↓              ↓
PostgreSQL    Bing API
    ↓              ↓
pgvector      Risk Analysis
```

## Quick Start

### 1. Local Development Setup

```bash
# Clone and setup
cd /path/to/project
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL with pgvector
docker-compose up -d

# Generate synthetic test data
python -m src.data.synthetic_pdf_generator

# Run tests
python -m pytest tests/

# Start FastAPI server
python -m src.api.main
```

### 2. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Ingest a document
curl -X POST "http://localhost:8000/ingest-document" \
  -F "applicant_id=TEST001" \
  -F "document_type=mvr" \
  -F "file=@data/samples/mvr_TEST001.pdf"

# Process underwriting
curl -X POST "http://localhost:8000/underwrite" \
  -H "Content-Type: application/json" \
  -d '{"applicant_id": "TEST001", "company_name": "Test Company"}'
```

### 3. AWS Lambda Deployment

```bash
# Set environment variables in AWS Lambda
# - DATABASE_URL
# - AWS_REGION
# - AWS_ACCESS_KEY_ID (if using IAM credentials locally)
# - AWS_SECRET_ACCESS_KEY (if using IAM credentials locally)
# - ANTHROPIC_API_KEY (optional)
# - BING_API_KEY (optional)

# Deploy via AWS Console or CLI
# 1. Create Lambda function
# 2. Upload code (or use container image)
# 3. Set handler to src.api.handler.handler
# 4. Configure API Gateway
# 5. Set up RDS PostgreSQL
```

### AWS CLI and Credentials

If you want to deploy from your machine, install the AWS CLI and configure credentials.

On macOS:

```bash
brew install awscli
aws --version
```

Or use the official installation script:

```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
aws --version
```

Then configure your credentials:

```bash
aws configure
```

Provide:
- `AWS Access Key ID`
- `AWS Secret Access Key`
- `Default region name` (for example `us-east-1`)
- `Default output format` (optional, e.g. `json`)

To verify credentials:

```bash
aws sts get-caller-identity
```

If you do not yet have credentials, create an IAM user or role in the AWS Console with permissions for Lambda, API Gateway, and RDS.

Then deploy the app by packaging your repository and uploading it to Lambda, or by using the AWS Console directly.

## API Endpoints

### POST /underwrite
Process an underwriting request.

**Request:**
```json
{
  "applicant_id": "APP001",
  "company_name": "ABC Trucking"
}
```

**Response:**
```json
{
  "applicant_id": "APP001",
  "decision": "accept",
  "premium": 1850.0,
  "reasoning": "Accepted with premium $1850 based on moderate risk profile",
  "cached": false
}
```

### POST /ingest-document
Upload and process a document.

**Form Data:**
- `applicant_id`: Applicant identifier
- `document_type`: "mvr", "loss_run", "inspection", or "policy"
- `file`: PDF file

### GET /decision/{applicant_id}
Retrieve cached underwriting decision.

### GET /health
Health check endpoint.

## Configuration

Environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# APIs (optional)
ANTHROPIC_API_KEY=your_claude_key
BING_API_KEY=your_bing_key

# LangSmith (optional)
LANGSMITH_API_KEY=your_langsmith_key
```

## Development

### Project Structure
```
src/
├── agent/          # LangGraph workflow
├── api/            # FastAPI endpoints
├── config/         # Settings and configuration
├── data/           # Synthetic data generation
├── premium/        # Premium calculation logic
├── retrieval/      # Document processing and vector search
├── security/       # Input validation and security
└── web_search/     # Bing search integration

tests/              # Unit and integration tests
docs/               # Documentation
```

### Running Tests
```bash
# Unit tests
pytest tests/test_basic.py -v

# With coverage
pytest --cov=src --cov-report=html
```

### Generating Test Data
```bash
# Generate synthetic PDFs
python -c "from src.data.synthetic_pdf_generator import generate_sample_documents; generate_sample_documents(5)"
```

## Deployment Options

### Option 1: AWS Lambda (Free Tier)
- **Cost**: ~$0/month (Lambda free tier + RDS free tier)
- **Setup**: Manual AWS Console configuration
- **Scaling**: Automatic

### Option 2: Local Development
- **Cost**: $0 (local PostgreSQL)
- **Setup**: Docker Compose
- **Use**: Development and testing

### Option 3: Full AWS (Production)
- **Cost**: ~$50-200/month
- **Setup**: Terraform/IaC
- **Features**: ECS, monitoring, auto-scaling

## Security Features

- **Input Validation**: Llama Guard pattern detection
- **Rate Limiting**: AWS WAF rules
- **Data Privacy**: PII masking in logs
- **HTTPS**: API Gateway encryption
- **Access Control**: IAM roles and policies

## Monitoring

### LangSmith Tracing
- View agent execution traces
- Debug decision-making process
- Monitor LLM calls and performance

### CloudWatch Metrics
- API latency and error rates
- Premium distribution analytics
- Database connection health

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check PostgreSQL
   docker-compose ps
   docker-compose logs postgres
   ```

2. **Import Errors**
   ```bash
   # Install missing dependencies
   pip install -r requirements.txt
   ```

3. **Lambda Timeout**
   - Increase timeout in Lambda configuration (max 15 minutes)
   - Optimize document processing for large PDFs

4. **API Gateway Errors**
   - Check API Gateway logs in CloudWatch
   - Verify IAM permissions for Lambda invocation

### Logs
```bash
# View application logs
tail -f /tmp/insurance_agent.log

# AWS Lambda logs
aws logs tail /aws/lambda/your-function-name --follow
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
