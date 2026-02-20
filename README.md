# 🔥 Trend Tracker

Cross-platform trend discovery tool for TikTok & Instagram Reels.

## Features

- 🔍 **Keyword-based search** - Find trending content by topic
- 📅 **Date filtering** - Focus on recent content (7/10/30 days)
- 🎯 **Metric prioritization** - Sort by views, comments, engagement, or trend score
- 🎵 **Audio matching** - Discover trending sounds
- 📊 **Engagement analytics** - Velocity tracking and scoring

## Quick Start

### 1. Installation

```bash
cd trend-tracker
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

```bash
cp .env.example .env
# Edit .env with your Instagram credentials (optional for now)
```

### 3. Initialize Database

```bash
python src/database/db_manager.py
```

### 4. Run the App

```bash
streamlit run app.py
```

The dashboard will open at [http://localhost:8501](http://localhost:8501)

## Usage

1. Enter a keyword (e.g., "dance tutorial")
2. Select date range and optimization metric
3. Click "Search"
4. Browse trending videos with metrics

## Project Status

✅ **Phase 1 MVP (Current)**
- [x] Project structure
- [x] Database schema
- [x] TikTok scraper (mock data)
- [x] Analytics/metrics module
- [x] Basic Streamlit dashboard
- [ ] Instagram scraper
- [ ] Real TikTok API integration
- [ ] Cross-platform audio matching

🚧 **Coming Soon**
- Instagram Reels integration
- Real-time data from TikTok/Instagram APIs
- Advanced velocity tracking
- Saved searches
- Export functionality

## Architecture

```
trend-tracker/
├── app.py                    # Main Streamlit app
├── src/
│   ├── scraper/             # TikTok & Instagram scrapers
│   ├── database/            # SQLite database manager
│   ├── analytics/           # Metrics & scoring
│   ├── matching/            # Cross-platform matching
│   └── utils/               # Helper functions
└── data/                    # SQLite database
```

## Development

### Test Components

```bash
# Test database
python src/database/db_manager.py

# Test TikTok scraper
python src/scraper/tiktok_scraper.py

# Test metrics
python src/analytics/metrics.py
```

## License

MIT
