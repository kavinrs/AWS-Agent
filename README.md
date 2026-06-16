# Agentic AWS Resource Manager

A LangChain + FastAPI AI agent that manages AWS resources through natural language, with a modern React chat interface.

## Architecture

```
User ──► React UI ──► FastAPI ──► AWS Agent ──► LLM (Claude / GPT-4o)
                                       │
                                  Tool Selection
                                       │
                         ┌─────────────┴──────────────┐
                    S3 Tools              CloudWatch Tools
                         │                            │
                    boto3 (S3)              boto3 (CloudWatch Logs)
```

## Project Structure

```
aws-agent-v2/
├── main.py                  # Backend entrypoint
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
├── agent/
│   └── aws_agent.py         # LangChain ReAct agent
├── api/
│   └── app.py               # FastAPI routes
├── tools/
│   ├── cloudwatch_tool.py   # CloudWatch LangChain tools
│   └── cloud_control_tool.py # AWS Cloud Control tools
└── frontend/                # React UI
    ├── src/
    │   ├── App.jsx          # Main chat interface
    │   ├── App.css          # Styling
    │   └── index.css        # Base styles
    └── package.json         # Node dependencies
```

## Setup

### 1. AWS IAM Setup

Create an IAM user and attach this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AWSAgentPolicy",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:ListBucket",
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation",
        "s3:GetBucketVersioning",
        "s3:PutBucketVersioning",
        "s3:PutPublicAccessBlock",
        "s3:ListObjectsV2",
        "s3:DeleteBucket",
        "cloudformation:ListResources",
        "cloudformation:GetResource",
        "cloudformation:CreateResource",
        "cloudformation:UpdateResource",
        "cloudformation:DeleteResource",
        "logs:DescribeLogGroups",
        "logs:FilterLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

Then generate **Access Keys** for the user.

### 2. Environment Variables

Edit `.env`:
```env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your_secret...
AWS_DEFAULT_REGION=us-east-1
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=anthropic
```

### 3. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the backend server
python main.py
```

Backend server starts at **http://localhost:8000**

### 4. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (if not already installed)
npm install

# Start the development server
npm run dev
```

Frontend will be available at **http://localhost:3000**

---

## Usage

1. **Start the backend**: Run `python main.py` from the root directory
2. **Start the frontend**: Run `npm run dev` from the `frontend` directory
3. **Open your browser**: Navigate to `http://localhost:3000`
4. **Start chatting**: Ask the AWS Agent to manage your resources!

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/health` | Health check |
| GET | `/tools` | List all agent tools |
| POST | `/chat` | Send message to agent |

### POST /chat

**Request:**
```json
{
  "message": "List all my S3 buckets"
}
```

**Response:**
```json
{
  "message": "List all my S3 buckets",
  "response": "You have 2 S3 buckets:\n1. my-app-bucket\n2. my-logs-bucket",
  "steps": [
    {
      "tool": "list_s3_buckets",
      "tool_input": "",
      "observation": "{\"status\": \"success\", \"buckets\": [...]}"
    }
  ],
  "duration_ms": 1842
}
```

---

## Example Prompts

```
"List all my S3 buckets"
"Create an S3 bucket called my-photos-2026"
"Show details of bucket my-app-bucket"
"Delete bucket old-test-bucket"
"List my CloudWatch log groups"
"Search for ERROR in /aws/lambda/my-function logs from the last 2 hours"
```

---

## Features

### Backend
- 🤖 LangChain ReAct agent with AWS tools
- 🔧 S3, CloudWatch, and Cloud Control API integration
- 📡 FastAPI REST API
- 🔄 CORS enabled for frontend integration

### Frontend
- 🎨 Modern dark theme UI
- 💬 Real-time chat interface
- 🔧 View available AWS tools
- 📊 See tool execution steps and timing
- ⚡ Fast and responsive React app

---

## Interactive Docs

Visit **http://localhost:8000/docs** for Swagger UI after starting the backend server.
