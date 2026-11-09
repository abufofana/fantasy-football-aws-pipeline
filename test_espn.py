
import os
from dotenv import load_dotenv
from espn_api.football import League

# Load credentials from the local .env file
load_dotenv()

league = League(
    league_id=int(os.environ["ESPN_LEAGUE_ID"]),
    year=int(os.environ["ESPN_YEAR"]),
    espn_s2=os.environ["ESPN_S2"],
    swid=os.environ["ESPN_SWID"]
)

print(f"Connected to: {league.settings.name}")
print(f"Number of teams: {len(league.teams)}")

for team in league.teams:
    print(f"- {team.team_name}")


print("\n=== LEAGUE ROSTERS ===")

for team in league.teams:
    print(f"\n{team.team_name}")

    for player in team.roster:
        print(
            f"  {player.name} | "
            f"{player.position} | "
            f"{player.lineupSlot} | "
            f"Status: {player.injuryStatus}"
        )

print("\n=== CURRENT WEEK MATCHUPS ===")

week = league.current_week
print(f"ESPN Fantasy Week: {week}")

matchups = league.box_scores(week)

for matchup in matchups:
    home = matchup.home_team
    away = matchup.away_team

    print(f"\n{home.team_name} vs {away.team_name}")
    print(f"Projected: {matchup.home_projected:.1f} - {matchup.away_projected:.1f}")
    print(f"Actual: {matchup.home_score:.1f} - {matchup.away_score:.1f}")




print("\n=== AVAILABLE FREE AGENTS ===")

positions = ["QB", "RB", "WR", "TE", "D/ST"]
all_free_agents = {}

for position in positions:
    players = league.free_agents(size=50, position=position)
    all_free_agents[position] = players

    print(f"\n{position}: {len(players)} players")

    for player in players:
        print(f"  {player.name} | {player.proTeam}")

print(
    f"\nTotal players retrieved: "
    f"{sum(len(p) for p in all_free_agents.values())}"
)


print("\n=== RECENT LEAGUE TRANSACTIONS ===")

activities = league.recent_activity(size=20)

print(f"Transactions retrieved: {len(activities)}")

for activity in activities:
    print("\n--- Transaction ---")

    for action in activity.actions:
        team, action_type, player = action[:3]

        player_name = getattr(player, "name", str(player))

        print(
            f"{team.team_name} | "
            f"{action_type} | "
            f"{player_name}"
        )
