import math


def get_rank(player_data: dict):
    if "prefix" in player_data:  # User has a prefix, let's use this for the rank
        open_bracket = player_data["prefix"].find("[")
        close_bracket = player_data["prefix"].find("]")
        return player_data["prefix"][open_bracket+1:close_bracket]
    if "rank" in player_data:  # Staff ranks + Youtuber
        if player_data["rank"] == "ADMIN":
            return "Admin"
        elif player_data["rank"] == "MODERATOR":
            return "Moderator"
        elif player_data["rank"] == "HELPER":
            return "Helper"
        elif player_data["rank"] == "YOUTUBER":
            return "Youtuber"
    elif "buildTeam" in player_data:
        if player_data["buildTeam"] is True:
            return "Build Team"
    elif "monthlyPackageRank" in player_data:  # recurring purchase, only MVP++ atm
        if player_data["monthlyPackageRank"] == "SUPERSTAR":
            return "MVP++"
    elif "newPackageRank" in player_data:  # post-EULA
        if player_data["newPackageRank"] == "MVP_PLUS":
            return "MVP+"
        elif player_data["newPackageRank"] == "MVP":
            return "MVP"
        elif player_data["newPackageRank"] == "VIP_PLUS":
            return "VIP+"
        elif player_data["newPackageRank"] == "VIP":
            return "VIP"
    elif "packageRank" in player_data:  # pre-EULA
        if player_data["packageRank"] == "MVP_PLUS":
            return "MVP+"
        elif player_data["packageRank"] == "MVP":
            return "MVP"
        elif player_data["packageRank"] == "VIP_PLUS":
            return "VIP+"
        elif player_data["packageRank"] == "VIP":
            return "VIP"
    elif bool(player_data):
        return ""
    else:
        return None


def get_network_level(exp: int):
    # Converted from https://github.com/Plancke/hypixel-php/blob/master/src/util/Leveling.php#L39
    base = 10000
    growth = 2500

    reverse_pq_prefix = -(base - 0.5 * growth) / growth
    reverse_const = reverse_pq_prefix * reverse_pq_prefix
    growth_divides_2 = 2 / growth

    return 1 if exp < 0 else math.floor(1 + reverse_pq_prefix + math.sqrt(reverse_const + growth_divides_2 * exp))


def get_achievement_points(achievement_list, data):
    """Gets achievement points"""
    points = 0
    for game in achievement_list:
        if "achievementsOneTime" in data:
            for item in achievement_list[game]["one_time"]:
                achvmt_name = "{}_{}".format(game, item.lower())
                achvmt = achievement_list[game]["one_time"][item]
                if achvmt_name in data["achievementsOneTime"]:
                    points += achvmt["points"]
        if "achievements" in data:
            for item in achievement_list[game]["tiered"]:
                achvmt_name = "{}_{}".format(game, item.lower())
                achvmt = achievement_list[game]["tiered"][item]
                for tier in achvmt["tiers"]:
                    if achvmt_name not in data["achievements"]:
                        break
                    if data["achievements"][achvmt_name] >= tier["amount"]:
                        points += tier["points"]
    return points


def count_quest_completions(data):
    total_completed = 0
    for quest in data["quests"]:
        if "completions" in data["quests"][quest]:
            total_completed += len(data["quests"][quest]["completions"])
    return total_completed
