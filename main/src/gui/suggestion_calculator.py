"""Suggestion calculator - calculates optimal activity arrangement based on user settings"""
from core.models import (
    ActivityCharacter, ActivityType, ActivityGoal, SuggestionUserSettings, ActivitySuggestion
)


def calculate_suggestion_for_all(characters: list[ActivityCharacter], global_settings: SuggestionUserSettings = None) -> ActivitySuggestion | None:
    """Calculate activity suggestion for all characters combined based on total remaining work"""
    # Aggregate remaining work across all characters
    remaining = get_remaining_all(characters)
    if remaining['total_grinding_remaining_value'] == 0 and remaining['total_star_remaining_value'] == 0:
        return None

    # Use global settings if provided, otherwise fall back to first character's settings
    if global_settings is not None:
        settings = global_settings
    else:
        # Use the first character's settings (backward compatibility)
        settings = SuggestionUserSettings()
        for char in characters:
            if char.grinding_goal or char.star_waiting_goal:
                settings = char.suggestion_settings
                break

    # Calculate available time after accounting for switching
    total_available_minutes = settings.daily_total_hours * 60

    # If we have both activities, we need to account for one switch if both are done
    has_both = remaining['total_grinding_remaining_value'] > 0 and remaining['total_star_remaining_value'] > 0
    if has_both:
        total_available_minutes -= settings.switch_minutes

    # Calculate how much we can do per day considering concurrency
    grinding_capacity_per_day = 0
    star_capacity_per_day = 0

    if remaining['total_grinding_remaining_value'] > 0:
        grinding_capacity_per_day = total_available_minutes * settings.grinding_concurrent

    if remaining['total_star_remaining_value'] > 0:
        star_capacity_per_day = total_available_minutes * settings.star_waiting_concurrent

    # If we have both, split time proportionally to remaining work
    if has_both:
        total_remaining_minutes = remaining['total_grinding_remaining_duration'] + remaining['total_star_remaining_duration']
        grinding_daily = (remaining['total_grinding_remaining_duration'] / total_remaining_minutes) * grinding_capacity_per_day
        star_daily = (remaining['total_star_remaining_duration'] / total_remaining_minutes) * star_capacity_per_day
    elif remaining['total_grinding_remaining_value'] > 0:
        grinding_daily = grinding_capacity_per_day
        star_daily = 0
    else:
        grinding_daily = 0
        star_daily = star_capacity_per_day

    # Calculate days remaining
    if grinding_daily > 0:
        grinding_days_remaining = max(1, remaining['total_grinding_remaining_duration'] / grinding_daily)
    else:
        grinding_days_remaining = 0

    if star_daily > 0:
        star_days_remaining = max(1, remaining['total_star_remaining_duration'] / star_daily)
    else:
        star_days_remaining = 0

    # Estimated days is max of the two since they can be done in parallel
    estimated_days = max(grinding_days_remaining, star_days_remaining)

    # Get estimated remaining income across all characters
    estimated_income = sum(char.get_remaining_income() for char in characters)

    # Generate recommendation with per-character details
    recommendation = generate_recommendation(
        characters,
        grinding_daily, star_daily, estimated_days, estimated_income,
        remaining['total_grinding_remaining_value'], remaining['total_star_remaining_value']
    )

    return ActivitySuggestion(
        daily_grinding_minutes=grinding_daily,
        daily_star_waiting_minutes=star_daily,
        estimated_days_remaining=estimated_days,
        estimated_total_income=estimated_income,
        recommendation=recommendation
    )


def calculate_suggestion(character: ActivityCharacter) -> ActivitySuggestion | None:
    """Calculate activity suggestion for a single character (keep for compatibility)"""
    return calculate_suggestion_for_all([character])


def get_remaining_all(characters: list[ActivityCharacter]) -> dict:
    """Get aggregated remaining work across all characters"""
    result = {
        'total_grinding_remaining_value': 0,
        'total_grinding_remaining_duration': 0,
        'total_star_remaining_value': 0,
        'total_star_remaining_duration': 0,
    }

    for char in characters:
        if char.grinding_goal:
            total_value, total_duration, _ = char.calculate_totals(ActivityType.GRINDING)
            result['total_grinding_remaining_value'] += max(0, char.grinding_goal.target_value - total_value)
            result['total_grinding_remaining_duration'] += max(0, char.grinding_goal.target_duration - total_duration)

        if char.star_waiting_goal:
            total_value, total_duration, _ = char.calculate_totals(ActivityType.STAR_WAITING)
            result['total_star_remaining_value'] += max(0, char.star_waiting_goal.target_value - total_value)
            result['total_star_remaining_duration'] += max(0, char.star_waiting_goal.target_duration - total_duration)

    return result


def get_remaining(character: ActivityCharacter) -> dict:
    """Get remaining work for both activities"""
    result = {
        'grinding_remaining_value': 0,
        'grinding_remaining_duration': 0,
        'star_remaining_value': 0,
        'star_remaining_duration': 0,
    }

    if character.grinding_goal:
        total_value, total_duration, _ = character.calculate_totals(ActivityType.GRINDING)
        result['grinding_remaining_value'] = max(0, character.grinding_goal.target_value - total_value)
        result['grinding_remaining_duration'] = max(0, character.grinding_goal.target_duration - total_duration)

    if character.star_waiting_goal:
        total_value, total_duration, _ = character.calculate_totals(ActivityType.STAR_WAITING)
        result['star_remaining_value'] = max(0, character.star_waiting_goal.target_value - total_value)
        result['star_remaining_duration'] = max(0, character.star_waiting_goal.target_duration - total_value)

    return result


def get_efficiency(character: ActivityCharacter) -> dict:
    """Get current efficiency from historical data"""
    result = {
        'grinding_value_per_hour': 0,
        'star_success_per_hour': 0,
    }

    # Grinding
    if character.grinding_goal:
        total_value, total_duration, _ = character.calculate_totals(ActivityType.GRINDING)
        if total_duration > 0:
            result['grinding_value_per_hour'] = (total_value / total_duration) * 60

    # Star waiting
    if character.star_waiting_goal:
        total_value, total_duration, _ = character.calculate_totals(ActivityType.STAR_WAITING)
        if total_duration > 0:
            result['star_success_per_hour'] = (total_value / total_duration) * 60

    return result


def generate_recommendation(
    characters: list[ActivityCharacter],
    grinding_daily: float,
    star_daily: float,
    estimated_days: float,
    estimated_income: int,
    remaining_grinding: int,
    remaining_star: int,
) -> str:
    """Generate human readable recommendation with per-character details"""
    parts = []

    # Add per-character breakdown
    has_any_grinding = any(
        char.grinding_goal and char.calculate_totals(ActivityType.GRINDING)[2] > 0
        for char in characters
    )
    has_any_star = any(
        char.star_waiting_goal and char.calculate_totals(ActivityType.STAR_WAITING)[2] > 0
        for char in characters
    )

    if has_any_grinding or has_any_star:
        parts.append("\n【各角色每日分配】")

        # Calculate total remaining duration for proportion distribution
        total_grinding_remaining_duration = sum(
            max(0, char.grinding_goal.target_duration - char.calculate_totals(ActivityType.GRINDING)[1])
            for char in characters if char.grinding_goal
        )

        total_star_remaining_duration = sum(
            max(0, char.star_waiting_goal.target_duration - char.calculate_totals(ActivityType.STAR_WAITING)[1])
            for char in characters if char.star_waiting_goal
        )

        for char in characters:
            char_has_grinding = char.grinding_goal and char.calculate_totals(ActivityType.GRINDING)[2] > 0
            char_has_star = char.star_waiting_goal and char.calculate_totals(ActivityType.STAR_WAITING)[2] > 0

            if char_has_grinding or char_has_star:
                char_line = f"\n{char.name}:"

                if char_has_grinding and total_grinding_remaining_duration > 0:
                    _, total_duration, remaining = char.calculate_totals(ActivityType.GRINDING)
                    remaining_duration = max(0, char.grinding_goal.target_duration - total_duration)
                    char_grinding_daily = (remaining_duration / total_grinding_remaining_duration) * grinding_daily
                    if char_grinding_daily > 0.1:
                        char_line += f" 搬砖 {char_grinding_daily:.0f} 分钟"

                if char_has_star and total_star_remaining_duration > 0:
                    _, total_duration, remaining = char.calculate_totals(ActivityType.STAR_WAITING)
                    remaining_duration = max(0, char.star_waiting_goal.target_duration - total_duration)
                    char_star_daily = (remaining_duration / total_star_remaining_duration) * star_daily
                    if char_star_daily > 0.1:
                        if char_has_grinding and char_grinding_daily > 0.1:
                            char_line += ","
                        char_line += f" 蹲星 {char_star_daily:.0f} 分钟"

                parts.append(char_line)

        parts.append("\n\n【总体安排】")

    # Overall summary
    if remaining_grinding > 0:
        parts.append(f"总计每日搬砖: {grinding_daily:.0f} 分钟")

    if remaining_star > 0:
        parts.append(f"总计每日蹲星: {star_daily:.0f} 分钟")

    if estimated_days <= 1:
        days_text = "今天就可以完成全部目标"
    elif estimated_days <= 3:
        days_text = f"预计 {estimated_days:.1f} 天可以完成全部目标"
    elif estimated_days <= 7:
        days_text = f"预计 {estimated_days:.1f} 天完成全部目标"
    elif estimated_days <= 30:
        days_text = f"预计 {estimated_days:.0f} 天完成全部目标，保持节奏"
    else:
        days_text = f"预计 {estimated_days:.0f} 天完成全部目标，目标很大，分段完成更轻松"

    parts.append(days_text)

    if estimated_income > 0:
        # Calculate what proportion of total remaining work will be done today
        total_remaining_duration = 0
        if grinding_daily > 0:
            grinding_total_remaining = sum(
                max(0, char.grinding_goal.target_duration - char.calculate_totals(ActivityType.GRINDING)[1])
                for char in characters if char.grinding_goal
            )
            total_remaining_duration += grinding_total_remaining
        if star_daily > 0:
            star_total_remaining = sum(
                max(0, char.star_waiting_goal.target_duration - char.calculate_totals(ActivityType.STAR_WAITING)[1])
                for char in characters if char.star_waiting_goal
            )
            total_remaining_duration += star_total_remaining

        if total_remaining_duration > 0:
            today_total_duration = grinding_daily + star_daily
            proportion = today_total_duration / total_remaining_duration
            today_income = estimated_income * proportion
            parts.append(f"完成今日建议，预计今日收入 {today_income:.0f} 人民币，")
        parts.append(f"全部完成还能获得 {estimated_income:,} 人民币收入")

    if remaining_grinding > 0 and remaining_star > 0:
        parts.append("搬砖和蹲星可以同时进行，充分利用时间")

    return "".join(parts) + "。"
