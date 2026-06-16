# AWS Agent Frontend

A modern React-based chat interface for the AWS Agent, built with Vite.

## Features

- 🎨 Modern dark theme UI
- 💬 Real-time chat interface
- 🔧 View available AWS tools
- 📊 See tool execution steps
- ⚡ Fast and responsive

## Setup

### Prerequisites

- Node.js 16+ installed
- Backend server running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
npm run preview
```

## Usage

1. Make sure the backend server is running at `http://localhost:8000`
2. Start the frontend with `npm run dev`
3. Open your browser to `http://localhost:3000`
4. Start chatting with the AWS Agent!

## Example Queries

- "List all my S3 buckets"
- "Show my CloudWatch log groups"
- "Create an S3 bucket called my-test-bucket-2026"
- "Search for ERROR in my CloudWatch logs"

## API Integration

The frontend connects to the backend API at `http://localhost:8000`:

- `GET /tools` - Fetch available tools
- `POST /chat` - Send messages to the agent

## Tech Stack

- React 19
- Vite 8
- CSS3 (Custom styling)
- Fetch API for HTTP requests
