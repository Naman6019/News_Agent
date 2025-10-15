# AI News Agent 🤖📰

An intelligent news agent that fetches RSS feeds, summarizes articles using local AI (Ollama), and delivers daily news digests via WhatsApp. Features automated morning (8 AM IST) and evening (6 PM IST) delivery.

## Features

- 📡 **RSS Feed Aggregation**: Fetches news from multiple sources across Technology, Business, Science, and World News
- 🤖 **Local AI-Powered Summarization**: Uses Ollama (local LLM) with gemma3:4b model for concise, engaging news summaries
- 📱 **WhatsApp Integration**: Delivers formatted news digests via Twilio WhatsApp API
- ⏰ **Automated Scheduling**: Daily delivery at 8 AM and 6 PM IST
- 🐳 **Docker Ready**: Easy deployment with Docker and docker-compose
- 🔧 **RESTful API**: Full API for manual operations and testing
- 📊 **Health Monitoring**: Built-in health checks and error reporting
- 💰 **Cost-Free AI**: No API costs - runs entirely on your local machine

## Quick Start

### Prerequisites

- Python 3.11+
- **Ollama** running locally with **gemma3:4b** model
- Twilio account with WhatsApp enabled
- Docker (optional, for containerized deployment)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd ai-news-agent
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Required: Ollama Configuration (Make sure Ollama is running locally)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b

# Required: Twilio WhatsApp Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890
WHATSAPP_RECIPIENT_NUMBER=+1234567890

# Optional: Customize delivery times (IST)
MORNING_DELIVERY_HOUR=8
EVENING_DELIVERY_HOUR=18
```

### 4. Run with Docker (Recommended)

```bash
docker-compose up --build
```

### 5. Run Locally

```bash
python -m app.main
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health & Status
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed service status
- `GET /api/v1/scheduler/status` - Scheduler status

### News Operations
- `GET /api/v1/news/digest` - Generate manual news digest
- `GET /api/v1/news/categories/{category}` - Get news by category
- `GET /api/v1/news/sources` - List RSS feed sources

### WhatsApp Operations
- `POST /api/v1/whatsapp/test` - Send test message
- `POST /api/v1/whatsapp/send-digest` - Send manual digest
- `GET /api/v1/whatsapp/validate` - Validate configuration

### Scheduler Operations
- `POST /api/v1/scheduler/trigger/{morning|evening}` - Manual delivery trigger
- `GET /api/v1/scheduler/next-runs` - Next scheduled deliveries

## Configuration

### News Categories

The agent monitors these categories with their RSS sources:

- **Technology**: CNN Tech, TechCrunch, The Verge
- **Business**: CNN Business, Business Insider, Financial Times
- **Science**: CNN Space, Science News, Nature
- **World News**: CNN World, BBC World, Al Jazeera

### Delivery Schedule

- **Morning**: 8:00 AM IST (configurable via `MORNING_DELIVERY_HOUR`)
- **Evening**: 6:00 PM IST (configurable via `EVENING_DELIVERY_HOUR`)

### Message Format

Messages are formatted for WhatsApp with:
- Clear category sections
- Concise AI-generated summaries
- Source attribution
- Timestamps in IST

## Development

### Project Structure

```
├── app/
│   ├── api/v1/endpoints/     # API route handlers
│   ├── core/                 # Configuration and logging
│   ├── services/             # Business logic services
│   └── main.py              # FastAPI application
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
├── docker-compose.yml      # Deployment configuration
└── .env.example           # Environment template
```

### Key Services

- **RSS Parser** (`rss_parser.py`): Fetches and parses RSS feeds
- **Summarizer** (`summarizer.py`): AI-powered article summarization
- **WhatsApp Service** (`whatsapp.py`): Twilio WhatsApp integration
- **Scheduler** (`scheduler.py`): Automated delivery management
- **News Service** (`news_service.py`): Main orchestration service

### Adding New RSS Sources

Edit `app/core/config.py`:

```python
NEWS_CATEGORIES = {
    "technology": [
        "https://example.com/rss",  # Add new source
        # ... existing sources
    ]
}
```

## Monitoring & Logs

- **Application Logs**: Written to `news_agent.log` and console
- **Health Checks**: Automated health monitoring via `/health` endpoint
- **Error Notifications**: WhatsApp alerts for critical errors
- **Scheduler Status**: Real-time scheduler status via API

## Troubleshooting

### Common Issues

1. **WhatsApp messages not sending**
   - Verify Twilio credentials in `.env`
   - Check phone number formats (must start with +)
   - Ensure WhatsApp is enabled in Twilio console

2. **RSS feeds not fetching**
   - Check RSS feed URLs in configuration
   - Verify internet connectivity
   - Check application logs for specific errors

3. **AI summarization failing**
   - Ensure Ollama is running (`ollama serve`)
   - Verify gemma3:4b model is installed (`ollama pull gemma3:4b`)
   - Check Ollama is accessible at `http://localhost:11434`
   - Review article content length limits

### Debug Mode

Enable debug logging:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

## Deployment Options

### Production Deployment

1. **Docker Compose** (Recommended)
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

2. **Manual Docker Build**
   ```bash
   docker build -t ai-news-agent .
   docker run -p 8000:8000 --env-file .env ai-news-agent
   ```

3. **Cloud Platforms**
   - Heroku: Add `Procfile` and deploy
   - Railway: Connect GitHub repo
   - AWS/GCP: Use container services

### Security Considerations

- Store Twilio credentials securely (environment variables)
- Use HTTPS in production
- Implement rate limiting for API endpoints
- Monitor WhatsApp message costs
- Regular credential rotation for Twilio

## Costs

- **Ollama (Local AI)**: Completely free - runs on your machine
- **Twilio WhatsApp**: ~$0.05 per message (depends on region)
- **RSS feeds**: Free

**Total AI Cost: $0** 🎉

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review application logs
3. Test individual services via API endpoints
4. Check service status via health endpoints

---

*Built with ❤️ using FastAPI, Ollama, Twilio, and Python*