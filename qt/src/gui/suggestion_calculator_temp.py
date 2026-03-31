"""Suggestion calculator - calculates optimal activity arrangement based on user settings"""
from src.core.models import (
    ActivityCharacter, ActivityType, ActivityGoal, SuggestionUserSettings, ActivitySuggestion,
    OptimizationAlgorithm
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
    # Constraint 1: each concurrent slot (whether grinding or star waiting) uses one character
    #            One character can only do one activity at a time
    # Constraint 2: actual concurrent slots cannot exceed number of characters we have
    # So total daily capacity is:
    # total_available_minutes per slot × min(grinding_concurrent + star_waiting_concurrent, number_of_characters)
    total_concurrent_slots = min(
        settings.grinding_concurrent + settings.star_waiting_concurrent,
        len([c for c in characters if c.grinding_goal or c.star_waiting_goal])
    )
    total_daily_capacity = total_available_minutes * total_concurrent_slots
    max_grinding_total = total_available_minutes * settings.grinding_concurrent
    max_star_total = total_available_minutes * settings.star_waiting_concurrent

    # Select allocation algorithm
    # Handle case where algorithm might be stored as string
    current_algorithm = settings.algorithm
    if isinstance(current_algorithm, str):
        try:
            current_algorithm = OptimizationAlgorithm(current_algorithm)
        except ValueError:
            current_algorithm = OptimizationAlgorithm.BALANCED

    if has_both and current_algorithm == OptimizationAlgorithm.DAILY_INCOME:
        # Daily income maximization: allocate to the activity with higher income per minute first
        # Calculate income per minute for each activity
        grinding_income_per_minute = 0
        if remaining['total_grinding_remaining_duration'] > 0:
            total_remaining_income_grinding = sum(
                char.get_remaining_income()
                for char in characters if char.grinding_goal and char.grinding_goal.total_income > 0
            )
            if total_remaining_income_grinding > 0:
                grinding_income_per_minute = total_remaining_income_grinding / remaining['total_grinding_remaining_duration']

        star_income_per_minute = 0
        if remaining['total_star_remaining_duration'] > 0:
            total_remaining_income_star = sum(
                char.get_remaining_income()
                for char in characters if char.star_waiting_goal and char.star_waiting_goal.total_income > 0
            )
            if total_remaining_income_star > 0:
                star_income_per_minute = total_remaining_income_star / remaining['total_star_remaining_duration']

        # Prioritize the activity with higher income per minute
        if grinding_income_per_minute >= star_income_per_minute:
            # Fill grinding first up to its maximum concurrent limit and total capacity
            grinding_daily = min(remaining['total_grinding_remaining_duration'], max_grinding_total, total_daily_capacity)
            grinding_daily = max(0, grinding_daily)
            # Remaining capacity to star
            remaining_capacity = max(0, total_daily_capacity - grinding_daily)
            star_daily = min(remaining['total_star_remaining_duration'], remaining_capacity, max_star_total)
            star_daily = max(0, star_daily)
        else:
            # Fill star first up to its maximum concurrent limit and total capacity
            star_daily = min(remaining['total_star_remaining_duration'], max_star_total, total_daily_capacity)
            star_daily = max(0, star_daily)
            # Remaining capacity to grinding
            remaining_capacity = max(0, total_daily_capacity - star_daily)
            grinding_daily = min(remaining['total_grinding_remaining_duration'], remaining_capacity, max_grinding_total)
            grinding_daily = max(0, grinding_daily)
    elif has_both:
        # Default: Balanced completion - proportional allocation by remaining duration
        # This achieves "total income maximization" by finishing all goals as soon as possible
        total_remaining_minutes = remaining['total_grinding_remaining_duration'] + remaining['total_star_remaining_duration']
        # Proportional allocation within capacity, but respect max per-activity concurrency
        grinding_daily = (remaining['total_grinding_remaining_duration'] / total_remaining_minutes) * total_daily_capacity
        # Cannot exceed maximum concurrent slots for this activity type
        grinding_daily = min(grinding_daily, max_grinding_total)
        grinding_daily = max(0, grinding_daily)
        # Remaining capacity goes to star waiting
        remaining_capacity = max(0, total_daily_capacity - grinding_daily)
        star_daily = min(
            (remaining['total_star_remaining_duration'] / total_remaining_minutes) * total_daily_capacity,
            remaining_capacity,
            max_star_total
        )
        star_daily = max(0, star_daily)
    elif remaining['total_grinding_remaining_value'] > 0:
        # Only grinding, use all grinding concurrent slots (capped by actual characters)
        max_grinding = min(settings.grinding_concurrent, total_concurrent_slots)
        grinding_daily = total_available_minutes * max_grinding
        grinding_daily = min(grinding_daily, remaining['total_grinding_remaining_duration'])
        grinding_daily = max(0, grinding_daily)
        star_daily = 0
    else:
        # Only star waiting, use all star waiting concurrent slots (capped by actual characters)
        max_star = min(settings.star_waiting_concurrent, total_concurrent_slots)
        grinding_daily = 0
        star_daily = total_available_minutes * max_star
        star_daily = min(star_daily, remaining['total_star_remaining_duration'])
        star_daily = max(0, star_daily)

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
        result['star_remaining_duration'] = max(0, character.star_waiting_goal.target_duration - total_duration)

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

    # Calculate total remaining duration for proportion distribution
    total_grinding_remaining_duration = sum(
        max(0, char.grinding_goal.target_duration - char.calculate_totals(ActivityType.GRINDING)[1])
        for char in characters if char.grinding_goal
    )

    total_star_remaining_duration = sum(
        max(0, char.star_waiting_goal.target_duration - char.calculate_totals(ActivityType.STAR_WAITING)[1])
        for char in characters if char.star_waiting_goal
    )

    # Filter characters that have remaining work
    active_characters = [
        char for char in characters
        if (char.grinding_goal and char.calculate_totals(ActivityType.GRINDING)[2] > 0) or
           (char.star_waiting_goal and char.calculate_totals(ActivityType.STAR_WAITING)[2] > 0)
    ]

    if active_characters:
        parts.append("\n【各角色详细安排】\n")
        parts.append("┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐\n")
        parts.append("│ 角色名称 │ 每日搬砖 │ 每日蹲星 │ 剩余银币 │ 剩余时长 │ 预计天数 │\n")
        parts.append("├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤\n")

        # Get daily calendar time limit per character (same for all characters)
        daily_calendar_minutes = None
        try:
            if active_characters and hasattr(active_characters[0], 'suggestion_settings'):
                daily_calendar_minutes = active_characters[0].suggestion_settings.daily_total_hours * 60
        except:
            pass
        if daily_calendar_minutes is None or daily_calendar_minutes <= 0:
            daily_calendar_minutes = 8 * 60  # Default 8 hours

        # Simple Iterative Projection Method
        # Algorithm (Combettes, 2002 - Projection Methods for Convex Feasibility Problems):
        # 1. Start: gᵢ ∝ remaining_gᵢ, sᵢ ∝ remaining_sᵢ  (keep proportional allocation)
        # 2. Repeat until convergence:
        #    a. For each character: if gᵢ + sᵢ > daily_limit → scale proportionally to fit
        #    b. Renormalize global totals: Σgᵢ = grinding_daily, Σsᵢ = star_daily
        # 3. This simple method is proven to converge and very robust in practice
        # Reference: https://en.wikipedia.org/wiki/Projection_method_(optimization)

        # Step 1: Initial allocation
        allocations = []
        for char in active_characters:
            _, total_g_duration, remaining_g_value = char.calculate_totals(ActivityType.GRINDING)
            _, total_s_duration, remaining_s_value = char.calculate_totals(ActivityType.STAR_WAITING)

            remaining_g = max(0, char.grinding_goal.target_duration - total_g_duration) if char.grinding_goal else 0.0
            remaining_s = max(0, char.star_waiting_goal.target_duration - total_s_duration) if char.star_waiting_goal else 0.0

            # Initial proportional allocation - keep the original proportion
            if char.grinding_goal and total_grinding_remaining_duration > 0:
                g = (remaining_g / total_grinding_remaining_duration) * grinding_daily
            else:
                g = 0.0

            if char.star_waiting_goal and total_star_remaining_duration > 0:
                s = (remaining_s / total_star_remaining_duration) * star_daily
            else:
                s = 0.0

            # Initial bounds clamping
            g = max(0.0, min(g, remaining_g))
            s = max(0.0, min(s, remaining_s))

            allocations.append({
                'char': char,
                'g': g,
                's': s,
                'max_g': remaining_g,
                'max_s': remaining_s,
                'max_total': daily_calendar_minutes,
                'total_g_duration': total_g_duration,
                'total_s_duration': total_s_duration,
                'remaining_g_value': remaining_g_value,
                'remaining_s_value': remaining_s_value,
            })

        # Step 2: Iterative projection - simple and robust
        max_iterations = 100
        tolerance = 1e-3
        for iter_num in range(max_iterations):
            any_violation = False

            # Project onto per-character individual constraints:
            # 0 ≤ g ≤ max_g, 0 ≤ s ≤ max_s, g + s ≤ max_total
            for alloc in allocations:
                g = alloc['g']
                s = alloc['s']
                mg = alloc['max_g']
                ms = alloc['max_s']
                mt = alloc['max_total']

                # Box bound projection
                g = max(0.0, min(g, mg))
                s = max(0.0, min(s, ms))

                # Sum bound projection - if violated, scale proportionally
                if g + s > mt + 1e-9 and mt > 0:
                    scale = mt / (g + s)
                    g *= scale
                    s *= scale
                    any_violation = True

                # Update and check for change
                if abs(g - alloc['g']) > tolerance or abs(s - alloc['s']) > tolerance:
                    alloc['g'] = g
                    alloc['s'] = s
                    any_violation = True
                else:
                    alloc['g'] = g
                    alloc['s'] = s

            # Project onto global sum constraints - maintain target totals
            total_g = sum(a['g'] for a in allocations)
            total_s = sum(a['s'] for a in allocations)

            # Global rescaling
            if total_g > 1e-9 and grinding_daily > 0:
                scale_g = grinding_daily / total_g
                for alloc in allocations:
                    alloc['g'] *= scale_g

            if total_s > 1e-9 and star_daily > 0:
                scale_s = star_daily / total_s
                for alloc in allocations:
                    alloc['s'] *= scale_s

            # Check convergence
            total_g_after = sum(a['g'] for a in allocations)
            total_s_after = sum(a['s'] for a in allocations)

            if not any_violation and abs(total_g_after - grinding_daily) < tolerance and abs(total_s_after - star_daily) < tolerance:
                break  # converged

        # Final hard clamping - guarantee all constraints are satisfied
        for alloc in allocations:
            alloc['g'] = max(0.0, min(alloc['g'], alloc['max_g']))
            alloc['s'] = max(0.0, min(alloc['s'], alloc['max_s']))
            if alloc['g'] + alloc['s'] > alloc['max_total'] + 1e-9 and alloc['max_total'] > 0:
                # Final projection - this should never happen after iteration
                scale = alloc['max_total'] / (alloc['g'] + alloc['s'])
                alloc['g'] *= scale
                alloc['s'] *= scale

        # Final global renormalization
        total_g_final = sum(a['g'] for a in allocations)
        total_s_final = sum(a['s'] for a in allocations)
        if total_g_final > 1e-9 and grinding_daily > 0:
            scale_g = grinding_daily / total_g_final
            for alloc in allocations:
                alloc['g'] *= scale_g
        if total_s_final > 1e-9 and star_daily > 0:
            scale_s = star_daily / total_s_final
            for alloc in allocations:
                alloc['s'] *= scale_s

        # Build table with final result - all constraints are guaranteed to be satisfied
        for alloc in allocations:
            char = alloc['char']
            char_g_daily = alloc['g']
            char_s_daily = alloc['s']
            total_g_duration = alloc['total_g_duration']
            total_s_duration = alloc['total_s_duration']
            remaining_g_value = alloc['remaining_g_value']
            remaining_s_value = alloc['remaining_s_value']

            # Skip if no activity after projection
            if char_g_daily <= 0.1 and char_s_daily <= 0.1:
                continue

            # Calculate remaining value (silver/success)
            remaining_value = 0
            if char.grinding_goal and char.grinding_goal.target_value > 0:
                remaining_value += max(0, char.grinding_goal.target_value - remaining_g_value)
            if char.star_waiting_goal and char.star_waiting_goal.target_value > 0:
                remaining_value += max(0, char.star_waiting_goal.target_value - remaining_s_value)

            # Calculate character estimated days
            char_remaining_duration = 0
            if char_g_daily > 0 and char.grinding_goal:
                remaining_g_duration = max(0, char.grinding_goal.target_duration - total_g_duration)
                char_remaining_duration += remaining_g_duration / char_g_daily if char_g_daily > 0 else 0
            if char_s_daily > 0 and char.star_waiting_goal:
                remaining_s_duration = max(0, char.star_waiting_goal.target_duration - total_s_duration)
                char_remaining_duration += remaining_s_duration / char_s_daily if char_s_daily > 0 else 0

            # Format table row
            g_daily_str = f"{char_g_daily:.0f}'" if char_g_daily > 0.1 else "-"
            s_daily_str = f"{char_s_daily:.0f}'" if char_s_daily > 0.1 else "-"
            rv_str = f"{remaining_value:,}" if remaining_value > 0 else "-"

            remaining_total_duration = 0
            if char.grinding_goal:
                remaining_total_duration += max(0, char.grinding_goal.target_duration - total_g_duration)
            if char.star_waiting_goal:
                remaining_total_duration += max(0, char.star_waiting_goal.target_duration - total_s_duration)

            days_str = f"{char_remaining_duration:.1f}" if char_remaining_duration > 0 else "-"

            # Truncate name if too long
            name = char.name[:8] if len(char.name) > 8 else char.name.ljust(8)
            name = name.center(8)

            g_daily_str = g_daily_str.center(8)
            s_daily_str = s_daily_str.center(8)
            rv_str = rv_str.center(8)
            rd_str = f"{remaining_total_duration}".center(8)
            days_str = days_str.center(8)

            parts.append(f"│{name}│{g_daily_str}│{s_daily_str}│{rv_str}│{rd_str}│{days_str}│\n")

        parts.append("└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘\n")

    # Overall summary
    parts.append("\n【总体统计】\n")
    total_daily = grinding_daily + star_daily
    parts.append(f"• 所有角色合计每日总活动时长：{total_daily:.0f} 分钟\n")
    if remaining_grinding > 0:
        parts.append(f"• 其中搬砖合计：{grinding_daily:.0f} 分钟（多角色同时进行，总时间超过日历时长正常）\n")
    if remaining_star > 0:
        parts.append(f"• 其中蹲星合计：{star_daily:.0f} 分钟（多角色同时进行，总时间超过日历时长正常）\n")

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
    parts.append(f"• {days_text}\n")

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
            parts.append(f"• 完成今日建议，预计今日收入：{today_income:.0f} 人民币\n")
        parts.append(f"• 全部完成还能获得：{estimated_income:,} 人民币\n")

    if remaining_grinding > 0 and remaining_star > 0:
        parts.append("\n搬砖和蹲星使用不同角色，可以同时进行，充分利用时间。")

    return "".join(parts)
