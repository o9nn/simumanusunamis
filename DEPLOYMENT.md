# Deployment Guide: Reverie Generative Agents

This guide covers deploying the Reverie Generative Agents simulation as a production-ready system for autonomous agent interaction.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Local Development Setup](#local-development-setup)
5. [Docker Deployment](#docker-deployment)
6. [Production Deployment](#production-deployment)
7. [API Reference](#api-reference)
8. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
9. [Security Considerations](#security-considerations)

---

## Quick Start

### Using Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-repo/simumanusunamis.git
cd simumanusunamis

# 2. Copy and configure environment
cp .env.example .env
# Edit .env with your OpenAI API key and other settings

# 3. Start services
docker-compose up -d

# 4. Access the simulation
# Frontend: http://localhost
# API: http://localhost/api/v1/simulation/status
```

### Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure backend
# Create reverie/backend_server/utils.py with your API key

# 4. Start servers (in separate terminals)
# Terminal 1 - Frontend:
cd environment/frontend_server
python manage.py runserver

# Terminal 2 - Backend:
cd reverie/backend_server
python reverie.py
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         NGINX (Port 80/443)                      │
│  - SSL termination                                               │
│  - Static file serving                                           │
│  - Rate limiting                                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Django Frontend (Port 8000)                   │
│  - Web UI for simulation visualization                          │
│  - REST API for external agent integration                      │
│  - WebSocket support for real-time events                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
┌──────────────────────┐   ┌─────────────────────────────────────┐
│   PostgreSQL DB      │   │     Reverie Backend (Python)        │
│  - Session data      │   │  - Agent cognition (LLM calls)      │
│  - User auth         │   │  - Simulation state management      │
│                      │   │  - Memory/planning/reflection        │
└──────────────────────┘   └──────────────────┬──────────────────┘
                                              │
                                              ▼
                           ┌──────────────────────────────────────┐
                           │           OpenAI API                  │
                           │  - GPT-3.5/4 for agent reasoning     │
                           │  - Embeddings for memory retrieval   │
                           └──────────────────────────────────────┘
```

### Key Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| Frontend Server | Web UI & API | Django 2.2 |
| Backend Server | Agent simulation | Python (Reverie) |
| Database | Persistence | PostgreSQL (prod) / SQLite (dev) |
| Cache | Session & API cache | Redis |
| Reverse Proxy | SSL, routing | Nginx |

---

## Prerequisites

### System Requirements

- **Python**: 3.9 or higher
- **RAM**: Minimum 4GB (8GB+ recommended for multiple agents)
- **Storage**: 10GB+ for simulation data
- **Docker**: 20.10+ (for containerized deployment)

### API Keys

- **OpenAI API Key**: Required for agent cognition
  - Get from: https://platform.openai.com/api-keys
  - Recommended: Set spending limits

---

## Local Development Setup

### 1. Environment Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Backend Server

Create `reverie/backend_server/utils.py`:

```python
# Copy and paste your OpenAI API Key
openai_api_key = "sk-your-key-here"
key_owner = "YourName"

# Path configurations (default values work for standard layout)
maze_assets_loc = "../../environment/frontend_server/static_dirs/assets"
env_matrix = f"{maze_assets_loc}/the_ville/matrix"
env_visuals = f"{maze_assets_loc}/the_ville/visuals"
fs_storage = "../../environment/frontend_server/storage"
fs_temp_storage = "../../environment/frontend_server/temp_storage"
collision_block_id = "32125"
debug = True
```

### 3. Start Servers

**Terminal 1 - Frontend Server:**
```bash
cd environment/frontend_server
python manage.py migrate
python manage.py runserver
```

**Terminal 2 - Backend Server:**
```bash
cd reverie/backend_server
python reverie.py
```

### 4. Run Simulation

1. Open browser: http://localhost:8000/simulator_home
2. In backend terminal, enter:
   - Fork simulation: `base_the_ville_isabella_maria_klaus`
   - New simulation name: `test-sim-1`
   - Run steps: `run 100`

---

## Docker Deployment

### Development Mode

```bash
# Start all services
docker-compose up

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Mode

```bash
# Build images
docker-compose build

# Configure environment
cp .env.example .env
# Edit .env with production settings

# Start in detached mode
docker-compose up -d

# Check health
docker-compose ps
curl http://localhost/api/v1/simulation/status
```

### Configuration

Key environment variables (see `.env.example`):

```bash
# Required
OPENAI_API_KEY=sk-your-key
DJANGO_SECRET_KEY=your-secure-key

# Recommended for production
DJANGO_DEBUG=False
REQUIRE_API_AUTH=True
API_KEYS=key1,key2
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Generate secure `DJANGO_SECRET_KEY`
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Configure `DJANGO_ALLOWED_HOSTS`
- [ ] Set up SSL certificates
- [ ] Configure OpenAI API key (use secrets manager)
- [ ] Set up backup for `/storage` directory
- [ ] Configure monitoring

### SSL Configuration

1. Obtain SSL certificates (Let's Encrypt recommended)
2. Place in `docker/ssl/`:
   - `fullchain.pem`
   - `privkey.pem`
3. Uncomment HTTPS section in `docker/nginx.conf`

### Scaling Considerations

- **Multiple Agents**: Each agent makes LLM calls; monitor API costs
- **Concurrent Users**: Use Redis for session storage
- **Simulation Storage**: Consider S3 for large simulations

---

## API Reference

### Base URL

```
http://localhost/api/v1
```

### Authentication

Include API key in header:
```
X-API-Key: your-api-key
```

Or as query parameter:
```
?api_key=your-api-key
```

### Health Check Endpoints

Health check endpoints do not require authentication.

#### GET /health
Basic health check for load balancers and monitoring.

**Response:**
```json
{
  "status": "healthy",
  "service": "reverie-frontend",
  "timestamp": "2023-02-13T15:20:00.000Z",
  "checks": {
    "storage": "ok",
    "temp_storage": "ok",
    "simulation": "active",
    "database": "ok"
  }
}
```

#### GET /api/v1/health/detailed
Detailed health check with system metrics.

**Response:**
```json
{
  "status": "healthy",
  "service": "reverie-frontend",
  "checks": {...},
  "details": {
    "simulation_count": 5,
    "active_simulation": {
      "sim_code": "test-sim-1",
      "step": 150,
      "agent_count": 3
    },
    "pending_whispers": 2
  }
}
```

### Simulation Endpoints

#### GET /simulation/status
Get current simulation status.

**Response:**
```json
{
  "status": "active",
  "sim_code": "test-sim-1",
  "step": 150,
  "curr_time": "February 13, 2023, 03:20:00",
  "agent_count": 3,
  "persona_names": ["Isabella Rodriguez", "Klaus Mueller", "Maria Lopez"]
}
```

### Agent Endpoints

#### GET /agents
List all agents in simulation.

**Response:**
```json
{
  "agent_count": 3,
  "agents": [
    {
      "name": "Isabella Rodriguez",
      "position": {"x": 72, "y": 14},
      "currently": "planning Valentine's Day party",
      "current_action": "working at Hobbs Cafe counter"
    }
  ]
}
```

#### GET /agents/{name}/state
Get detailed agent state.

**Response:**
```json
{
  "name": "Isabella Rodriguez",
  "position": {"x": 72, "y": 14},
  "identity": {
    "age": 34,
    "innate": "friendly, outgoing, hospitable",
    "currently": "planning Valentine's Day party"
  },
  "current_state": {
    "act_description": "working at the cafe counter",
    "chatting_with": null
  },
  "daily_schedule": [...],
  "memory_summary": {
    "total_events": 45,
    "total_thoughts": 12,
    "total_chats": 8
  }
}
```

#### GET /agents/{name}/relationships
Get agent's social network and relationship strengths.

**Response:**
```json
{
  "agent": "Isabella Rodriguez",
  "relationship_count": 2,
  "relationships": [
    {
      "name": "Klaus Mueller",
      "interactions": 15,
      "strength": "strong",
      "sentiment": "positive",
      "recent_topics": ["research", "coffee", "weather"]
    },
    {
      "name": "Maria Lopez",
      "interactions": 8,
      "strength": "moderate",
      "sentiment": "neutral",
      "recent_topics": ["party", "work"]
    }
  ]
}
```

#### POST /agents/{name}/whisper
Inject a goal or memory into an agent.

**Request:**
```json
{
  "content": "Remember to meet Klaus at the park at 3pm",
  "type": "thought"
}
```

**Response:**
```json
{
  "status": "success",
  "agent": "Isabella Rodriguez",
  "pending_whispers": 1
}
```

### Multi-Agent Interaction Endpoints

#### POST /broadcast
Broadcast a goal or announcement to multiple agents at once.

**Request:**
```json
{
  "content": "There's a party at the town square at 5pm!",
  "type": "event",
  "target_agents": "all"
}
```

Or target specific agents:
```json
{
  "content": "Emergency meeting at the cafe",
  "type": "announcement",
  "target_agents": ["Isabella Rodriguez", "Klaus Mueller"]
}
```

**Response:**
```json
{
  "status": "success",
  "broadcast_id": "20230213152000",
  "content": "There's a party at the town square at 5pm!",
  "type": "event",
  "agents_notified": 3,
  "target_agents": ["Isabella Rodriguez", "Klaus Mueller", "Maria Lopez"]
}
```

#### GET /interactions
Get recent interactions between agents.

**Query Parameters:**
- `limit`: Max interactions to return (default: 50, max: 200)
- `agent`: Filter to interactions involving a specific agent

**Response:**
```json
{
  "sim_code": "test-sim-1",
  "count": 25,
  "filter_agent": null,
  "interactions": [
    {
      "agent": "Isabella Rodriguez",
      "node_id": "node_123",
      "created": "February 13, 2023, 14:30:00",
      "description": "Isabella talked to Klaus about the party",
      "poignancy": 7,
      "keywords": ["party", "planning", "Klaus"]
    }
  ]
}
```

#### GET /social-network
Get the full social network graph of agent relationships.

**Response:**
```json
{
  "sim_code": "test-sim-1",
  "node_count": 3,
  "edge_count": 3,
  "nodes": [
    {
      "id": "Isabella Rodriguez",
      "label": "Isabella Rodriguez",
      "type": "agent",
      "currently": "planning Valentine's Day party",
      "innate": "friendly, outgoing, hospitable"
    }
  ],
  "edges": [
    {
      "source": "Isabella Rodriguez",
      "target": "Klaus Mueller",
      "weight": 15,
      "strength": "strong"
    }
  ]
}
```

### World State Endpoints

#### GET /world/snapshot
Export full world state.

**Response:**
```json
{
  "sim_code": "test-sim-1",
  "step": 150,
  "metadata": {...},
  "agents": {
    "Isabella Rodriguez": {
      "position": {"x": 72, "y": 14},
      "act_description": "..."
    }
  }
}
```

---

## Monitoring & Troubleshooting

### Viewing Logs

```bash
# Docker logs
docker-compose logs -f frontend
docker-compose logs -f backend

# Application logs (production)
tail -f /var/log/reverie/django.log
```

### Common Issues

#### "No active simulation"
- Ensure backend server is running
- Check `temp_storage/curr_sim_code.json` exists

#### OpenAI Rate Limits
- Reduce simulation speed
- Use local embeddings: `REVERIE_EMBEDDING_MODEL=BAAI/bge-small-en`
- Enable TextGen fallback for local LLM

#### Memory Issues
- Reduce agent count
- Increase Docker memory limits
- Clear old simulation data

### Health Checks

```bash
# Frontend health
curl http://localhost/health

# API status
curl http://localhost/api/v1/simulation/status

# Database connection
docker-compose exec db pg_isready
```

---

## Security Considerations

### API Authentication

Enable in production:
```bash
REQUIRE_API_AUTH=True
API_KEYS=secure-random-key-1,secure-random-key-2
```

### Rate Limiting

Configured in Nginx:
- API endpoints: 10 requests/second
- General: 30 requests/second

### Secrets Management

- Never commit `.env` or API keys
- Use Docker secrets or Vault in production
- Rotate API keys regularly

### Network Security

- Use HTTPS in production
- Configure firewall rules
- Limit container networking

---

## Support

For issues and feature requests, please open a GitHub issue.
