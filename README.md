# Valorant MCP Server

A Model Context Protocol (MCP) server that provides comprehensive Valorant player statistics and match data through integration with the Henrik API. This server allows Claude Desktop to fetch player information, match history, rank data, and perform performance analysis for Valorant players.

## Features

- **Player Account Information**: Get player details including PUUID, display name, tag, and account level
- **Rank & MMR Data**: Fetch current competitive rank and peak rank information
- **Match History**: Retrieve recent match data with detailed statistics
- **Performance Analysis**: Analyze player performance across multiple matches with win rates, K/D ratios, and averages
- **Flexible Filtering**: Filter matches by game mode (competitive, unrated, deathmatch, spikerush)

## Prerequisites

- Python 3.8 or higher
- Henrik API key (get one from [Henrik Dev API](https://docs.henrikdev.xyz/valorant.html))
- Claude Desktop application

## Installation

### 1. Clone or Download the Server

Save the `valorant.py` file to your desired location.

### 2. Install Dependencies

```bash
pip install aiohttp pydantic mcp
```

Or using a virtual environment:
```bash
python -m venv valorant_env
source valorant_env/bin/activate  # On Windows: valorant_env\Scripts\activate
pip install aiohttp pydantic mcp
```

### 3. Get Henrik API Key

1. Visit [Henrik Dev API Documentation](https://docs.henrikdev.xyz/valorant.html)
2. Follow their instructions to obtain an API key
3. Keep this key secure - you'll need it for configuration

## Configuration

### Claude Desktop Setup

Add the following to your `claude_desktop_config.json` file:

```json
{
  "mcpServers": {
    "valorant": {
      "command": "python",
      "args": ["/absolute/path/to/valorant.py"],
      "env": {
        "VAL_API_KEY": "your_henrik_api_key_here"
      }
    }
  }
}
```

#### Configuration Options

**Using full Python path** (recommended):
```json
{
  "mcpServers": {
    "valorant": {
      "command": "/full/path/to/python",
      "args": ["/absolute/path/to/valorant.py"],
      "env": {
        "VAL_API_KEY": "your_henrik_api_key_here"
      }
    }
  }
}
```

**Using uv**:
```json
{
  "mcpServers": {
    "valorant": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/valorant.py", "run", "valorant.py"],
      "env": {
        "VAL_API_KEY": "HDEV-a65abbc4-eac1-4bce-9206-98ef16e2d535"
      }
    }
  }
}
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `VAL_API_KEY` | Your Henrik API key | Yes |

## Available Tools

### `get_player_account`
Fetch basic account information for a Valorant player.

**Parameters:**
- `name` (string): Player's display name
- `tag` (string): Player's tag line

**Example:** Get account info for player "TenZ#NA1"

### `get_player_rank`
Get current competitive rank and peak rank information.

**Parameters:**
- `name` (string): Player's display name  
- `tag` (string): Player's tag line

**Returns:** Current tier, peak tier, and PUUID

### `get_match_history`
Retrieve recent match history with detailed statistics.

**Parameters:**
- `name` (string): Player's display name
- `tag` (string): Player's tag line
- `match_count` (int, optional): Number of matches to retrieve (max 20, default 5)
- `mode` (string, optional): Filter by game mode (competitive, unrated, deathmatch, spikerush)

**Returns:** List of recent matches with K/D/A, map, mode, and match results

### `analyze_player_performance`
Analyze player performance across multiple recent matches.

**Parameters:**
- `name` (string): Player's display name
- `tag` (string): Player's tag line
- `matches_to_analyze` (int, optional): Number of recent matches to analyze (default 5)

**Returns:** Comprehensive performance analysis including:
- Win rate percentage
- Average kills, deaths, assists
- K/D ratio
- Total statistics

## Available Resources

### Player Profile
`valorant://player/{name}/{tag}/profile`

Get a complete player profile including account info and rank data.

### Match History
`valorant://player/{name}/{tag}/matches/{count}`

Get formatted match history for easy reading.

## Usage Examples

### Basic Player Lookup
```
Get account information for player "Shroud#NA1"
```

### Performance Analysis
```
Analyze the recent performance of player "TenZ#TSM" over the last 10 matches
```

### Match History with Filtering
```
Get the last 15 competitive matches for player "Ninja#USA"
```

### Comparative Analysis
```
Compare the performance of "Player1#TAG1" and "Player2#TAG2"
```