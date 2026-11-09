
import json
import os
from datetime import datetime, timezone
from botocore.exceptions import ClientError

import boto3
from dotenv import load_dotenv
from espn_api.football import League


def get_espn_credentials():
    # Use local environment variables during development.
    load_dotenv()

    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        # In AWS Lambda, retrieve encrypted credentials.
        ssm = boto3.client("ssm", region_name="us-east-1")

        s2 = ssm.get_parameter(
            Name="/fantasy-agent/espn-s2",
            WithDecryption=True
        )["Parameter"]["Value"]

        swid = ssm.get_parameter(
            Name="/fantasy-agent/espn-swid",
            WithDecryption=True
        )["Parameter"]["Value"]

        return s2, swid

    return os.environ["ESPN_S2"], os.environ["ESPN_SWID"]


def save_snapshot(data):
    s3 = boto3.client("s3")
    bucket = os.environ["S3_BUCKET_NAME"]
    key = "latest.json"

    previous = None

    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        previous = json.loads(response["Body"].read())
    except ClientError as error:
        if error.response["Error"]["Code"] not in (
            "NoSuchKey", "404"
        ):
            raise

    changes = []

    if previous:
        old_teams = {
            team["team_id"]: team
            for team in previous["teams"]
        }

        for team in data["teams"]:
            old_team = old_teams.get(team["team_id"])
            if not old_team:
                continue

            old_players = {
                player["name"] for player in old_team["roster"]
            }
            new_players = {
                player["name"] for player in team["roster"]
            }

            for name in new_players - old_players:
                changes.append(
                    f"{team['team_name']} added {name}"
                )

            for name in old_players - new_players:
                changes.append(
                    f"{team['team_name']} dropped {name}"
                )

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data),
        ContentType="application/json"
    )

    return changes



def lambda_handler(event, context):
    espn_s2, swid = get_espn_credentials()

    league = League(
        league_id=int(os.environ["ESPN_LEAGUE_ID"]),
        year=int(os.environ["ESPN_YEAR"]),
        espn_s2=espn_s2,
        swid=swid
    )

    teams = []

    for team in league.teams:
        players = []

        for player in team.roster:
            players.append({
                "name": player.name,
                "position": player.position,
                "lineup_slot": player.lineupSlot,
                "injury_status": player.injuryStatus
            })

        teams.append({
            "team_name": team.team_name,
            "team_id": team.team_id,
            "roster": players
        })

    matchups = []

    for matchup in league.box_scores(league.current_week):
        matchups.append({
            "home_team": matchup.home_team.team_name,
            "away_team": matchup.away_team.team_name,
            "home_projected": matchup.home_projected,
            "away_projected": matchup.away_projected
        })

        
    # Retrieve available players
    free_agents = {}

    for position in ["QB", "RB", "WR", "TE", "D/ST"]:
        players = league.free_agents(size=50, position=position)

        free_agents[position] = [
            {
                "name": player.name,
                "nfl_team": player.proTeam,
                "position": player.position,
                "injury_status": player.injuryStatus
            }
            for player in players
        ]

    # Retrieve recent league transactions
    transactions = []

    for activity in league.recent_activity(size=20):
        for action in activity.actions:
            team, action_type, player = action[:3]

            transactions.append({
                "team": team.team_name,
                "action": action_type,
                "player": getattr(player, "name", str(player))
            })
   
    data = {
        "league_name": league.settings.name,
        "week": league.current_week,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "teams": teams,
        "matchups": matchups,
        "free_agents": free_agents,
        "transactions": transactions
    }

    changes = save_snapshot(data)
    data["changes"] = changes

    return {
        "statusCode": 200,
        "body": json.dumps(data)
    }


if __name__ == "__main__":
    result = lambda_handler({}, None)
    print(json.dumps(json.loads(result["body"]), indent=2))
