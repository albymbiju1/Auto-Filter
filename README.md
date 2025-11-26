# CineAI AutoFilter Bot 🎬

A production-ready, feature-rich Telegram bot for automatic file indexing, search, and streaming. Built with Python, Pyrogram, and supports multiple database backends.

## ✨ Features

### 🤖 Core Features
- **AutoFilter**: Automatic file indexing from linked channels
- **Search**: Inline and private message search with spell correction
- **Multi-Database Support**: MongoDB and PostgreSQL with runtime switching
- **Caching**: Redis support for improved performance
- **Rate Limiting**: Built-in user rate limiting
- **Logging**: Comprehensive logging with rotation

### 🎬 Media Features
- **Multiple File Types**: Video, Document, Photo, Audio support
- **Metadata Extraction**: Automatic title, year, quality, language detection
- **IMDB Integration**: Movie information, ratings, posters
- **Spell Check**: AI-powered typo correction
- **Quality Detection**: HD, FHD, UHD, HDR support
- **Language Support**: Multi-language content detection

### ⭐ Premium Features
- **Premium Plans**: Multiple subscription tiers
- **Referral System**: Earn premium by inviting friends
- **Payment Integration**: Stripe, PayPal support
- **Premium Content**: Exclusive files for premium users
- **Usage Limits**: Configurable limits for different plans

### 🔒 Security & Access Control
- **Force Subscribe**: Require users to join channels
- **Token Verification**: Protect premium content
- **Admin Controls**: Comprehensive admin panel
- **User Management**: Ban, mute, promote users
- **Role-Based Access**: Multiple user roles

### 🎥 Streaming & Sharing
- **Streaming Links**: Multiple player support
- **URL Shortener**: Built-in and external shorteners
- **Clone Feature**: Save files to personal collection
- **Auto Delete**: Configurable TTL for files
- **Multiple Players**: HLS, HTTP, torrent-stream support

### 🛠️ Advanced Features
- **Background Tasks**: Auto-indexing, cleanup jobs
- **Broadcast System**: Chunked messaging with rate limits
- **Statistics**: Detailed user and bot analytics
- **Image Editor**: Background removal and editing
- **Multi-Language**: Internationalization support
- **Custom Buttons**: Configurable UI elements

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Telegram Bot Token
- MongoDB or PostgreSQL database
- Redis (optional, for caching)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/cineai-autofilter-bot.git
cd cineai-autofilter-bot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run the bot**
```bash
python -m app.main
```

## ⚙️ Configuration

### Required Environment Variables

```env
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here
API_ID=your_api_id_here
API_HASH=your_api_hash_here

# Database Configuration
MONGO_URI=mongodb://localhost:27017/cineai_bot
# OR
PG_URI=postgresql+asyncpg://user:password@localhost:5432/cineai_bot

# Admin Configuration
ADMIN_USER_IDS=123456789,987654321
SUPER_ADMIN_ID=123456789
```

### Optional Features

```env
# Feature Toggles
FEATURE_TOGGLES={"PM_SEARCH":true,"AUTO_FILTER":true,"INLINE_SEARCH":true,"PREMIUM":false,"REFERRAL":false,"STREAM":false}

# External APIs
IMDB_API_KEY=your_imdb_api_key
SHORTENER_API_KEY=your_shortener_api_key

# Payment
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Caching
REDIS_URL=redis://localhost:6379/0
```

## 📊 Database Setup

### MongoDB (Recommended)

1. **Install MongoDB**
```bash
# Ubuntu/Debian
sudo apt-get install mongodb

# Docker
docker run -d -p 27017:27017 --name mongodb mongo
```

2. **Configure connection**
```env
MONGO_URI=mongodb://localhost:27017/cineai_bot
PRIMARY_DB=mongo
```

### PostgreSQL

1. **Install PostgreSQL**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# Docker
docker run -d -p 5432:5432 --name postgres -e POSTGRES_PASSWORD=password postgres
```

2. **Create database**
```sql
CREATE DATABASE cineai_bot;
CREATE USER cineai_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE cineai_bot TO cineai_user;
```

3. **Configure connection**
```env
PG_URI=postgresql+asyncpg://cineai_user:password@localhost:5432/cineai_bot
PRIMARY_DB=postgres
```

### Redis (Optional)

1. **Install Redis**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# Docker
docker run -d -p 6379:6379 --name redis redis
```

2. **Configure connection**
```env
REDIS_URL=redis://localhost:6379/0
```

## 🐳 Docker Deployment

### Using Docker Compose

1. **Create docker-compose.yml**
```yaml
version: '3.8'

services:
  bot:
    build: .
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - API_ID=${API_ID}
      - API_HASH=${API_HASH}
      - MONGO_URI=mongodb://mongo:27017/cineai_bot
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - mongo
      - redis
    restart: unless-stopped

  mongo:
    image: mongo:latest
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped

  redis:
    image: redis:alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  mongo_data:
  redis_data:
```

2. **Deploy**
```bash
docker-compose up -d
```

### Building from Source

```bash
docker build -t cineai-bot .
docker run -d --env-file .env cineai-bot
```

## ☁️ Cloud Deployment

### Railway

1. **Fork and connect repository to Railway**
2. **Set environment variables in Railway dashboard**
3. **Deploy automatically on push**

### Render

1. **Connect GitHub repository to Render**
2. **Configure environment variables**
3. **Deploy as Web Service**

### VPS Deployment

1. **Setup server**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3 python3-pip python3-venv git -y

# Clone repository
git clone https://github.com/yourusername/cineai-autofilter-bot.git
cd cineai-autofilter-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

2. **Configure systemd service**
```ini
# /etc/systemd/system/cineai-bot.service
[Unit]
Description=CineAI Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/cineai-autofilter-bot
Environment=PATH=/home/ubuntu/cineai-autofilter-bot/venv/bin
ExecStart=/home/ubuntu/cineai-autofilter-bot/venv/bin/python -m app.main
Restart=always

[Install]
WantedBy=multi-user.target
```

3. **Start service**
```bash
sudo systemctl enable cineai-bot
sudo systemctl start cineai-bot
sudo systemctl status cineai-bot
```

## 🔧 Admin Commands

### Basic Admin Commands
- `/addchannel <chat_id>` - Add channel for auto-indexing
- `/rmchannel <chat_id>` - Remove channel
- `/channels` - List all channels
- `/stats` - Bot statistics
- `/users` - User statistics
- `/broadcast <message>` - Broadcast to all users
- `/groupbroadcast <message>` - Broadcast to groups

### User Management
- `/ban <user_id> [reason]` - Ban user
- `/unban <user_id>` - Unban user
- `/mute <user_id> [duration]` - Mute user
- `/unmute <user_id>` - Unmute user
- `/promote <user_id>` - Promote to admin
- `/demote <user_id>` - Demote from admin

### Settings & Configuration
- `/setwelcome <message>` - Set welcome message
- `/setstart <message>` - Set start message
- `/setcaption <pattern>` - Set file caption pattern
- `/settutorial <button_text>` - Set tutorial button
- `/toggle <feature>` - Toggle feature on/off

### Premium Management
- `/grantpremium <user_id> <days>` - Grant premium
- `/revokepremium <user_id>` - Revoke premium
- `/premiumstats` - Premium statistics
- `/referralstats` - Referral statistics

## 🎮 User Commands

### Basic Commands
- `/start` - Start bot and show menu
- `/help` - Show help message
- `/search <query>` - Search for files
- `/stats` - Show your statistics
- `/profile` - Show your profile

### Premium Commands
- `/premium` - Premium information
- `/referral` - Referral system
- `/myref` - Your referral code
- `/tokenverify <token>` - Verify access token

## 🔌 API Integration

### IMDB Integration

1. **Get IMDB API key**
   - Visit [IMDB API](https://imdb-api.com/)
   - Register and get API key

2. **Configure**
```env
IMDB_API_KEY=your_imdb_api_key
FEATURE_TOGGLES={"IMDB_INTEGRATION":true}
```

### Payment Integration

#### Stripe
```env
PREMIUM_PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

#### PayPal
```env
PREMIUM_PAYMENT_PROVIDER=paypal
PAYPAL_CLIENT_ID=your_client_id
PAYPAL_CLIENT_SECRET=your_client_secret
```

### URL Shortener

#### Built-in
```env
SHORTENER_PROVIDER=database
CUSTOM_SHORTENER_DOMAIN=https://short.xyz
```

#### External (Bitly)
```env
SHORTENER_PROVIDER=bitly
SHORTENER_API_KEY=your_bitly_token
```

## 📈 Monitoring & Analytics

### Logs
- **Location**: `logs/` directory
- **Files**: `bot.log`, `errors.log`
- **Rotation**: Automatic log rotation

### Statistics
- **User Activity**: Searches, downloads, referrals
- **File Metrics**: Indexing, downloads, popularity
- **System Performance**: CPU, memory, disk usage
- **Error Tracking**: Comprehensive error logging

### Health Checks
```bash
# Check bot status
curl http://localhost:8000/health

# Database health
python -c "from services.database_service import DatabaseService; import asyncio; asyncio.run(DatabaseService().health_check())"

# Redis health
python -c "from services.redis_service import RedisService; import asyncio; asyncio.run(RedisService('redis://localhost:6379/0').health_check())"
```

## 🔒 Security Considerations

### Bot Token Security
- Never share your bot token
- Use environment variables
- Rotate tokens periodically
- Monitor bot activity

### Database Security
- Use strong passwords
- Enable SSL/TLS connections
- Regular backups
- Access control

### API Security
- Validate all inputs
- Rate limiting
- HTTPS for webhooks
- IP whitelisting if needed

## 🛠️ Development

### Local Development

1. **Setup development environment**
```bash
git clone https://github.com/yourusername/cineai-autofilter-bot.git
cd cineai-autofilter-bot
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

2. **Configure development environment**
```env
DEVELOPMENT=true
DEBUG=true
LOG_LEVEL=DEBUG
```

3. **Run tests**
```bash
pytest tests/
```

4. **Code formatting**
```bash
black app/ handlers/ services/ utils/ models/
flake8 app/ handlers/ services/ utils/ models/
```

### Adding New Features

1. **Create handler in `handlers/` directory**
2. **Add models in `models/` directory**
3. **Add services in `services/` directory**
4. **Update configuration in `app/config.py`**
5. **Add tests in `tests/` directory**

### Database Schema Updates

#### MongoDB
```python
# Add new field to model
class NewModel(BaseDocument):
    new_field: str = Field(...)

# Create index
await db.collection.create_index("new_field")
```

#### PostgreSQL
```python
# Add new column
await conn.execute("ALTER TABLE table_name ADD COLUMN new_field VARCHAR(255)")

# Create index
await conn.execute("CREATE INDEX idx_new_field ON table_name(new_field)")
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit changes** (`git commit -m 'Add amazing feature'`)
4. **Push to branch** (`git push origin feature/amazing-feature`)
5. **Open Pull Request**

### Code Standards
- Follow PEP 8
- Use type hints
- Add docstrings
- Write tests
- Update documentation

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Getting Help
- **Documentation**: Check this README and code comments
- **Issues**: Open an issue on GitHub
- **Discussions**: Join GitHub Discussions
- **Telegram**: Contact @your_support_username

### Common Issues

#### Bot doesn't start
- Check bot token is valid
- Verify API_ID and API_HASH
- Check database connection
- Review logs in `logs/bot.log`

#### Files not indexing
- Verify bot is admin in channel
- Check channel is linked
- Review AutoFilter settings
- Check file size limits

#### Search not working
- Verify search is enabled
- Check database connection
- Review search logs
- Check file indexing status

## 🎯 Roadmap

### Upcoming Features
- [ ] AI-powered content recommendations
- [ ] Advanced analytics dashboard
- [ ] Mobile app companion
- [ ] Web interface for admins
- [ ] Multi-bot clustering
- [ ] Advanced content filtering
- [ ] Scheduled broadcasts
- [ ] User groups and roles
- [ ] Content rating system
- [ ] API for third-party integration

### Performance Improvements
- [ ] Database optimization
- [ ] Caching improvements
- [ ] Parallel processing
- [ ] CDN integration
- [ ] Load balancing

## 📊 Statistics

- **Languages**: Python, SQL, NoSQL
- **Lines of Code**: ~15,000+
- **Features**: 30+ core features
- **Database Support**: MongoDB, PostgreSQL
- **Deployment Options**: Docker, VPS, Cloud

---

**Built with ❤️ by the CineAI Team**

For support: 📧 support@cineai.bot | 🌐 [cineai.bot](https://cineai.bot)