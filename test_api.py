import asyncio
import os
import sys
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Import the fetch functions from valorant.py
try:
    import valorant
except ImportError as e:
    print(f"Error importing valorant.py: {e}")
    sys.exit(1)

async def test_player(name: str, tag: str):
    print(f"=== Testing Henrik API for Player: {name}#{tag} ===")
    
    try:
        # 1. Fetch Account Info
        print("\n1. Fetching Account Info...")
        account = await valorant.fetch_account_info(name, tag)
        if account:
            print(f"   Success! Account level: {account.account_level}")
            print(f"   PUUID: {account.puuid}")
            
            # 2. Fetch MMR / Rank Info
            print("\n2. Fetching MMR / Rank Info...")
            mmr = await valorant.fetch_mmr_info(account.puuid)
            if mmr:
                print(f"   Success! Current Tier: {mmr.current_tier}")
                print(f"   Peak Tier: {mmr.peak_tier}")
            else:
                print("   MMR/Rank info not found or unauthorized.")
        else:
            print("   Player account not found. Make sure the name and tag are correct.")
            return

        # 3. Fetch Match History
        print("\n3. Fetching Match History (recent 3 matches)...")
        matches = await valorant.fetch_match_history(name, tag, size=3)
        if matches:
            print(f"   Success! Retrieved {len(matches)} matches:")
            for i, m in enumerate(matches, 1):
                map_name = m.map or "Unknown Map"
                mode = m.mode or "Unknown Mode"
                kda = f"{m.kills}/{m.deaths}/{m.assists}"
                won = "Win" if (m.rounds_won and m.rounds_lost and m.rounds_won > m.rounds_lost) else "Loss"
                score = f"{m.rounds_won}-{m.rounds_lost}" if (m.rounds_won is not None) else "N/A"
                print(f"     Match {i}: {map_name} ({mode}) - {won} ({score}) | KDA: {kda}")
        else:
            print("   No matches retrieved (or public match history disabled for this player).")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Cleanup the session
        await valorant.cleanup()

if __name__ == "__main__":
    # Check if API key is configured
    api_key = os.getenv("VAL_API_KEY")
    if not api_key:
        print("Error: VAL_API_KEY environment variable is not set in .env or system environment.")
        sys.exit(1)
        
    # Get player name and tag from arguments or default to a active/known profile
    # Henrik Dev API works best with public accounts.
    name = "TenZ"
    tag = "NA1"
    
    if len(sys.argv) > 2:
        name = sys.argv[1]
        tag = sys.argv[2]
    elif len(sys.argv) == 2 and "#" in sys.argv[1]:
        parts = sys.argv[1].split("#")
        name = parts[0]
        tag = parts[1]
    
    print(f"Using API Key: {api_key[:6]}...{api_key[-4:] if len(api_key) > 10 else ''}")
    asyncio.run(test_player(name, tag))
