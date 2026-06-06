#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession

load_dotenv()

# Server configuration
mcp = FastMCP(
    "Valorant Player Stats",
    instructions="A server that provides access to Valorant player statistics and match data via the Henrik API."
)

# Henrik API configuration
VAL_API_KEY = os.getenv("VAL_API_KEY")
if not VAL_API_KEY:
    raise ValueError("VAL_API_KEY environment variable is required")

HENRIK_BASE_URL = "https://api.henrikdev.xyz"

# Data models for structured output
class AccountInfo(BaseModel):
    """Player account information structure."""
    puuid: str = Field(description="Player UUID")
    name: str = Field(description="Display name")
    tag: str = Field(description="Tag line")
    account_level: int = Field(description="Account level")
    region: Optional[str] = Field(description="Riot region", default="na")


class MMRInfo(BaseModel):
    """MMR/Rank information structure."""
    puuid: str = Field(description="Player UUID")
    current_tier: Optional[str] = Field(description="Current competitive tier", default=None)
    peak_tier: Optional[str] = Field(description="Peak competitive tier", default=None)

class MatchData(BaseModel):
    """Match data structure."""
    map: Optional[str] = Field(description="Map name", default=None)
    match_id: Optional[str] = Field(description="Match ID", default=None)
    game_start_patched: Optional[str] = Field(description="Game start time", default=None)
    mode: Optional[str] = Field(description="Game mode", default=None)
    kills: Optional[int] = Field(description="Player kills", default=None)
    deaths: Optional[int] = Field(description="Player deaths", default=None)
    assists: Optional[int] = Field(description="Player assists", default=None)
    team: Optional[str] = Field(description="Team color", default=None)
    rounds_won: Optional[int] = Field(description="Rounds won by team", default=None)
    rounds_lost: Optional[int] = Field(description="Rounds lost by team", default=None)

class PlayerAnalysis(BaseModel):
    """Player performance analysis."""
    player: str = Field(description="Player name#tag")
    matches_analyzed: int = Field(description="Number of matches analyzed")
    win_rate_percent: float = Field(description="Win rate percentage")
    average_kills: float = Field(description="Average kills per match")
    average_deaths: float = Field(description="Average deaths per match")
    average_assists: float = Field(description="Average assists per match")
    kd_ratio: float = Field(description="Kill/Death ratio")
    total_kills: int = Field(description="Total kills across matches")
    total_deaths: int = Field(description="Total deaths across matches")
    total_assists: int = Field(description="Total assists across matches")

# HTTP client session
_session: Optional[aiohttp.ClientSession] = None

async def get_session() -> aiohttp.ClientSession:
    """Get or create HTTP session."""
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session

async def fetch_from_henrik(endpoint: str) -> Optional[Dict[str, Any]]:
    """Fetch data from Henrik API."""
    url = f"{HENRIK_BASE_URL}{endpoint}"
    headers = {"Authorization": VAL_API_KEY}
    
    session = await get_session()
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"HTTP {response.status}: {response.reason}")
                return None
            return await response.json()
    except Exception as e:
        print(f"Error fetching {endpoint}: {str(e)}")
        return None

async def fetch_account_info(name: str, tag: str) -> Optional[AccountInfo]:
    """Fetch account information from Henrik API."""
    res = await fetch_from_henrik(f"/valorant/v2/account/{name}/{tag}")
    if not res or not res.get("data"):
        return None
    
    data = res["data"]
    return AccountInfo(
        puuid=data.get("puuid", ""),
        name=data.get("name", ""),
        tag=data.get("tag", ""),
        account_level=data.get("account_level", 0),
        region=data.get("region", "na")
    )

async def fetch_mmr_info(puuid: str, region: str = "na") -> Optional[MMRInfo]:
    """Fetch MMR information from Henrik API."""
    res = await fetch_from_henrik(f"/valorant/v3/by-puuid/mmr/{region}/pc/{puuid}")
    if not res or not res.get("data"):
        return None
    
    data = res["data"]
    current_tier = None
    peak_tier = None
    
    if data.get("current") and data["current"].get("tier"):
        current_tier = data["current"]["tier"].get("name")
    
    if data.get("peak") and data["peak"].get("tier"):
        peak_tier = data["peak"]["tier"].get("name")
    
    return MMRInfo(
        puuid=data.get("account", {}).get("puuid", puuid),
        current_tier=current_tier,
        peak_tier=peak_tier
    )

async def fetch_match_history(name: str, tag: str, size: int = 5, mode: Optional[str] = None, start: int = 0) -> List[MatchData]:
    """Fetch match history from Henrik API."""
    # Resolve official account information to get correct region and casing
    account = await fetch_account_info(name, tag)
    if not account:
        return []
    
    region = account.region or "na"
    official_name = account.name
    official_tag = account.tag

    endpoint = f"/valorant/v3/matches/{region}/{official_name}/{official_tag}?size={size}"
    if mode:
        endpoint += f"&mode={mode}"
    if start > 0:
        endpoint += f"&start={start}"
    
    res = await fetch_from_henrik(endpoint)
    if not res or not res.get("data"):
        return []
    
    matches = []
    for match in res["data"]:
        metadata = match.get("metadata", {})
        players_data = match.get("players", {})
        all_players = players_data.get("all_players", [])
        
        # Find the player in all_players using case-insensitive name/tag comparison
        player = None
        for p in all_players:
            if p.get("name", "").lower() == official_name.lower() and p.get("tag", "").lower() == official_tag.lower():
                player = p
                break
        
        if not player:
            continue
        
        # Get team info
        team_color = player.get("team", "").lower() if player.get("team") else None
        
        # Get rounds won/lost
        rounds_won = None
        rounds_lost = None
        if match.get("teams") and team_color and match["teams"].get(team_color):
            rounds_won = match["teams"][team_color].get("rounds_won")
            rounds_lost = match["teams"][team_color].get("rounds_lost")
        
        # Get mode
        mode_val = metadata.get("mode_id") or metadata.get("mode")
        
        # Get stats
        stats = player.get("stats", {})
        
        match_data = MatchData(
            map=metadata.get("map"),
            match_id=metadata.get("matchid"),
            game_start_patched=metadata.get("game_start_patched"),
            mode=mode_val,
            kills=stats.get("kills"),
            deaths=stats.get("deaths"),
            assists=stats.get("assists"),
            team=team_color,
            rounds_won=rounds_won,
            rounds_lost=rounds_lost
        )
        
        matches.append(match_data)
    
    return matches

# Tools
@mcp.tool()
async def get_player_account(
    name: str,
    tag: str,
    ctx: Context[ServerSession, None]
) -> AccountInfo:
    """Get basic account information for a Valorant player.
    
    Args:
        name: Player's display name (e.g., "SomePlayer")
        tag: Player's tag line (e.g., "NA1")
    """
    await ctx.info(f"Fetching account info for {name}#{tag}")
    
    try:
        account_info = await fetch_account_info(name, tag)
        if not account_info:
            raise Exception("Player not found or API error")
        
        await ctx.info(f"Successfully retrieved account info for level {account_info.account_level} player")
        return account_info
    except Exception as e:
        await ctx.error(f"Failed to fetch account info: {str(e)}")
        raise

@mcp.tool()
async def get_player_rank(
    name: str,
    tag: str,
    ctx: Context[ServerSession, None]
) -> MMRInfo:
    """Get current competitive rank information for a Valorant player.
    
    Args:
        name: Player's display name
        tag: Player's tag line
    """
    await ctx.info(f"Fetching rank info for {name}#{tag}")
    
    try:
        # First get account info to get PUUID
        account_info = await fetch_account_info(name, tag)
        if not account_info:
            raise Exception("Player not found")
        
        mmr_info = await fetch_mmr_info(account_info.puuid, account_info.region or "na")
        if not mmr_info:
            raise Exception("MMR info not available")
        
        await ctx.info(f"Player current tier: {mmr_info.current_tier}, peak tier: {mmr_info.peak_tier}")
        return mmr_info
    except Exception as e:
        await ctx.error(f"Failed to `fetch` rank info: {str(e)}")
        raise

@mcp.tool()
async def get_match_history(
    name: str,
    tag: str,
    ctx: Context[ServerSession, None],
    match_count: int = 5,
    mode: Optional[str] = None
) -> List[MatchData]:
    """Get recent match history for a Valorant player.
    
    Args:
        name: Player's display name
        tag: Player's tag line
        match_count: Number of recent matches to retrieve (max 20)
        mode: Game mode filter (competitive, unrated, deathmatch, spikerush)
    """
    if match_count > 20:
        match_count = 20
        await ctx.warning("Match count limited to 20")
    
    await ctx.info(f"Fetching {match_count} recent matches for {name}#{tag}")
    
    try:
        matches = await fetch_match_history(name, tag, match_count, mode)
        await ctx.info(f"Successfully retrieved {len(matches)} matches")
        return matches
    except Exception as e:
        await ctx.error(f"Failed to fetch match history: {str(e)}")
        raise

@mcp.tool()
async def analyze_player_performance(
    name: str,
    tag: str,
    ctx: Context[ServerSession, None],
    matches_to_analyze: int = 5
) -> PlayerAnalysis:
    """Analyze a player's recent performance across multiple matches.
    
    Args:
        name: Player's display name
        tag: Player's tag line  
        matches_to_analyze: Number of recent matches to include in analysis
    """
    await ctx.info(f"Analyzing performance for {name}#{tag} across {matches_to_analyze} matches")
    
    try:
        matches = await fetch_match_history(name, tag, matches_to_analyze)
        
        if not matches:
            raise Exception("No matches found for analysis")
        
        # Calculate statistics
        total_matches = len(matches)
        wins = 0
        total_kills = 0
        total_deaths = 0
        total_assists = 0
        
        for match in matches:
            # Count wins (more rounds won than lost)
            if match.rounds_won and match.rounds_lost and match.rounds_won > match.rounds_lost:
                wins += 1
            
            # Accumulate stats
            if match.kills is not None:
                total_kills += match.kills
            if match.deaths is not None:
                total_deaths += match.deaths
            if match.assists is not None:
                total_assists += match.assists
        
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
        avg_kills = total_kills / total_matches if total_matches > 0 else 0
        avg_deaths = total_deaths / total_matches if total_matches > 0 else 0
        avg_assists = total_assists / total_matches if total_matches > 0 else 0
        kd_ratio = total_kills / total_deaths if total_deaths > 0 else total_kills
        
        analysis = PlayerAnalysis(
            player=f"{name}#{tag}",
            matches_analyzed=total_matches,
            win_rate_percent=round(win_rate, 1),
            average_kills=round(avg_kills, 1),
            average_deaths=round(avg_deaths, 1),
            average_assists=round(avg_assists, 1),
            kd_ratio=round(kd_ratio, 2),
            total_kills=total_kills,
            total_deaths=total_deaths,
            total_assists=total_assists
        )
        
        await ctx.info(f"Analysis complete: {win_rate:.1f}% win rate, {kd_ratio:.2f} K/D ratio")
        return analysis
        
    except Exception as e:
        await ctx.error(f"Failed to analyze performance: {str(e)}")
        raise

# Resources
@mcp.resource("valorant://player/{name}/{tag}/profile")
async def get_player_profile(name: str, tag: str) -> str:
    """Get complete player profile including account info and rank."""
    try:
        account_info = await fetch_account_info(name, tag)
        if not account_info:
            return f"Error: Player {name}#{tag} not found"
        
        mmr_info = await fetch_mmr_info(account_info.puuid, account_info.region or "na")
        
        profile_text = f"""Player Profile: {name}#{tag}
Account Level: {account_info.account_level}
PUUID: {account_info.puuid}"""
        
        if mmr_info:
            profile_text += f"""
Current Rank: {mmr_info.current_tier or 'Unranked'}
Peak Rank: {mmr_info.peak_tier or 'No peak rank'}"""
        else:
            profile_text += "\nRank Info: Not available"
        
        return profile_text
    except Exception as e:
        return f"Error fetching profile for {name}#{tag}: {str(e)}"

@mcp.resource("valorant://player/{name}/{tag}/matches/{count}")
async def get_player_matches(name: str, tag: str, count: str) -> str:
    """Get formatted match history for a player."""
    try:
        match_count = min(int(count), 20)
        matches = await fetch_match_history(name, tag, match_count)
        
        if not matches:
            return f"No recent matches found for {name}#{tag}"
        
        result = f"Recent {len(matches)} matches for {name}#{tag}:\n\n"
        for i, match in enumerate(matches, 1):
            map_name = match.map or "Unknown Map"
            kda = f"{match.kills or 0}/{match.deaths or 0}/{match.assists or 0}"
            mode = match.mode or "Unknown Mode"
            
            result_text = "Win" if (match.rounds_won and match.rounds_lost and match.rounds_won > match.rounds_lost) else "Loss"
            
            result += f"Match {i}: {map_name} ({mode}) - {result_text}\n"
            result += f"  K/D/A: {kda}\n"
            if match.rounds_won is not None and match.rounds_lost is not None:
                result += f"  Score: {match.rounds_won}-{match.rounds_lost}\n"
            result += "\n"
        
        return result
    except Exception as e:
        return f"Error fetching matches: {str(e)}"

# Prompts
@mcp.prompt()
def analyze_player_performance_prompt(name: str, tag: str) -> str:
    """Generate a prompt for analyzing a Valorant player's performance."""
    return f"""Please analyze the Valorant performance of player {name}#{tag}.

Use the available tools to:
1. Get their current account information and level
2. Check their current competitive rank
3. Review their recent match history (last 5-10 games)
4. Analyze their overall performance statistics

Based on this data, provide insights about:
- Their current skill level and rank
- Performance trends in recent matches
- Kill/Death/Assist ratios and consistency
- Areas for potential improvement
- How they compare to players at their rank

Please be constructive and focus on actionable feedback."""

@mcp.prompt()
def compare_players_prompt(player1_name: str, player1_tag: str, player2_name: str, player2_tag: str) -> str:
    """Generate a prompt for comparing two Valorant players."""
    return f"""Compare the performance and statistics of two Valorant players:

Player 1: {player1_name}#{player1_tag}
Player 2: {player2_name}#{player2_tag}

For each player, gather:
1. Current rank information
2. Recent match performance (last 5-10 games)
3. Account level and experience
4. Performance analysis

Then provide a detailed comparison covering:
- Rank differences and competitive standing
- Recent performance trends and statistics
- Strengths and weaknesses of each player
- Who might be improving faster
- K/D ratios and consistency

Keep the analysis objective and constructive."""

# Cleanup function
async def cleanup():
    """Cleanup resources."""
    global _session
    if _session and not _session.closed:
        await _session.close()

if __name__ == "__main__":
    import atexit
    
    # Register cleanup
    atexit.register(lambda: asyncio.run(cleanup()))
    
    # Run the server over SSE transport if PORT env var is present (e.g., in Cloud Run)
    # otherwise default to stdio
    port_env = os.getenv("PORT")
    if port_env:
        import logging
        logging.basicConfig(level=logging.INFO)
        print(f"Starting MCP server on SSE transport on port {port_env}")
        mcp.run(transport="sse", host="0.0.0.0", port=int(port_env))
    else:
        mcp.run()