"""Suggestion calculator - calculates optimal activity arrangement based on user settings"""
import sys
from src.core.models import (
    ActivityCharacter, ActivityType, ActivityGoal, SuggestionUserSettings, ActivitySuggestion,
    OptimizationAlgorithm, DailyTask
)
from typing import List, Optional


def calculate_suggestion_for_all(
    characters: list[ActivityCharacter],
    global_settings: SuggestionUserSettings = None,
    daily_tasks: Optional[List[DailyTask]] = None
) -> ActivitySuggestion | None:
    """Calculate activity suggestion for all characters combined based on total remaining work
    If daily_tasks is provided, will prioritize allocating time to meet daily task requirements first
    """
    # print(f"[DEBUG] === calculate_suggestion_for_all start ===")
    # if global_settings:
    #     print(f"[DEBUG] Input global_settings daily_total_hours={global_settings.daily_total_hours}")
    # Aggregate remaining work across all characters
    remaining = get_remaining_all(characters)
    if remaining['total_grinding_remaining_value'] == 0 and remaining['total_star_remaining_value'] == 0:
        # Even if there's no remaining goal work, we might still have daily tasks
        if not daily_tasks:
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

    # print(f"[DEBUG] Final settings daily_total_hours={settings.daily_total_hours}")
    # Calculate available time after accounting for switching
    total_available_minutes = settings.daily_total_hours * 60

    # Handle daily tasks - allocate required time first (priority)
    # Group by character: for each character, sum of all daily tasks cannot exceed daily calendar time
    daily_calendar_minutes = settings.daily_total_hours * 60
    # print(f"[DEBUG] daily_calendar_minutes per character = {daily_calendar_minutes}")
    daily_required_by_char: dict[str, dict[ActivityType, int]] = {}

    if daily_tasks:
        for task in daily_tasks:
            if not task.enabled:
                continue
            if task.character_name not in daily_required_by_char:
                daily_required_by_char[task.character_name] = {
                    ActivityType.GRINDING: 0,
                    ActivityType.STAR_WAITING: 0,
                }
            daily_required_by_char[task.character_name][task.activity_type] += task.target_minutes


        # Enforce constraint: for each character, total daily <= daily_calendar_minutes
        # If exceeds, scale proportionally to fit
        # print(f"[DEBUG] Before constraint, number of daily tasks: {len(daily_required_by_char)}")
        # for char_name, requirements in daily_required_by_char.items():
        #     total_required = requirements[ActivityType.GRINDING] + requirements[ActivityType.STAR_WAITING]
        #     print(f"[DEBUG] Character {char_name}: daily tasks sum = {total_required} minutes")
        #     if total_required > daily_calendar_minutes:
        #         original_g = requirements[ActivityType.GRINDING]
        #         original_s = requirements[ActivityType.STAR_WAITING]
        #         # Need to scale down to fit
        #         scale = daily_calendar_minutes / total_required
        #         requirements[ActivityType.GRINDING] = int(requirements[ActivityType.GRINDING] * scale)
        #         requirements[ActivityType.STAR_WAITING] = int(requirements[ActivityType.STAR_WAITING] * scale)
        #         print(f"[DEBUG] → Scaled: {requirements[ActivityType.GRINDING]}+{requirements[ActivityType.STAR_WAITING]}={requirements[ActivityType.GRINDing]+requirements[ActivityType.STAR_WAITING]}")
        #         # Ensure at least 0 if rounding made it zero
        #         if requirements[ActivityType.GRINDING] == 0 and requirements[ActivityType.STAR_WAITING] == 0:
        #             # Give priority to whichever was larger originally
        #             if original_g > original_s:
        #                 requirements[ActivityType.GRINDING] = daily_calendar_minutes
        #             else:
        #                 requirements[ActivityType.STAR_WAITING] = daily_calendar_minutes
        #     else:
        #         print(f"[DEBUG] → OK, within limit {daily_calendar_minutes}")

    # Sum across all characters for global allocation
    daily_required_grinding = sum(
        reqs[ActivityType.GRINDING] for reqs in daily_required_by_char.values()
    )
    daily_required_star = sum(
        reqs[ActivityType.STAR_WAITING] for reqs in daily_required_by_char.values()
    )

    # Only subtract switching time if we actually need to switch activities on the same character
    # If both grinding and star waiting are done on different characters at the same time,
    # no switching is needed - so don't subtract anything!
    # We need switching only when a single character does both activities in one day.
    # But in general optimal allocation, we won't do that - each character does one activity.
    # So only subtract switching when we have both activities AND some character needs both.
    # For backward compatibility, we keep the original behavior: if has_both → subtract once.
    # The user explained: switching time is for switching between different characters when one goes offline.
    # If you have fixed number of concurrent slots = grinding_concurrent + star_waiting_concurrent,
    # you don't need to switch at all - each character stays in its activity all day.
    # So no switching time needed when concurrent slots are fully used by fixed assignments.
    # Only subtract switching if you actually need to switch during the day.
    # User's use case: 1 grinding + 1 star waiting on two different characters → no switch needed.
    # So we DON'T subtract any switching time in this case!
    #
    # The correct rule: only need switching if total active characters > total concurrent slots.
    # Because that means you need to rotate (switch) characters during the day.
    # If total active characters <= total concurrent slots → no switching needed, everyone stays online.
    #
    total_active_chars = len([c for c in characters if c.grinding_goal or c.star_waiting_goal])
    total_concurrent_slots = settings.grinding_concurrent + settings.star_waiting_concurrent
    has_both = remaining['total_grinding_remaining_value'] > 0 and remaining['total_star_remaining_value'] > 0
    need_switching = total_active_chars > total_concurrent_slots
    if need_switching:
        # Assume one switching per day average
        total_available_minutes -= settings.switch_minutes

    # Calculate how much we can do per day considering concurrency
    # Constraint 1: each concurrent slot (whether grinding or star waiting) uses one character
    #            One character can only do one activity at a time
    # Constraint 2: actual concurrent slots cannot exceed number of characters we have
    # If we have daily tasks, allocate required time FIRST then use remaining for overall goals
    total_concurrent_slots = min(
        settings.grinding_concurrent + settings.star_waiting_concurrent,
        len([c for c in characters if c.grinding_goal or c.star_waiting_goal or (daily_tasks and any(t.character_name == c.name for t in daily_tasks))])
    )
    total_daily_capacity = total_available_minutes * total_concurrent_slots

    # Actual maximum concurrent slots after considering number of characters
    actual_max_grinding_slots = min(settings.grinding_concurrent, total_concurrent_slots)
    actual_max_star_slots = min(settings.star_waiting_concurrent, total_concurrent_slots)
    max_grinding_total = total_available_minutes * actual_max_grinding_slots
    max_star_total = total_available_minutes * actual_max_star_slots

    # With daily tasks: we must satisfy daily requirements first, then allocate remaining to overall goals
    # Clamp required to not exceed maximum concurrent limits
    daily_required_grinding = min(daily_required_grinding, max_grinding_total)
    daily_required_star = min(daily_required_star, max_star_total)
    daily_required_total = daily_required_grinding + daily_required_star

    # Remaining capacity after allocating for daily tasks
    remaining_capacity_after_daily = max(0, total_daily_capacity - daily_required_total)
    remaining_grinding_max = max(0, max_grinding_total - daily_required_grinding)
    remaining_star_max = max(0, max_star_total - daily_required_star)

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
        # With daily tasks: daily tasks are already allocated first, we allocate remaining capacity to maximize income
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

        # Start with daily requirements
        grinding_daily = daily_required_grinding
        star_daily = daily_required_star

        # Prioritize the activity with higher income per minute for remaining capacity
        if grinding_income_per_minute >= star_income_per_minute:
            # Fill remaining grinding capacity first
            additional_grinding = min(remaining['total_grinding_remaining_duration'] - grinding_daily, remaining_grinding_max, remaining_capacity_after_daily)
            additional_grinding = max(0, additional_grinding)
            grinding_daily += additional_grinding
            remaining_capacity = max(0, remaining_capacity_after_daily - additional_grinding)
            additional_star = min(remaining['total_star_remaining_duration'] - star_daily, remaining_star_max, remaining_capacity)
            additional_star = max(0, additional_star)
            star_daily += additional_star
        else:
            # Fill remaining star capacity first
            additional_star = min(remaining['total_star_remaining_duration'] - star_daily, remaining_star_max, remaining_capacity_after_daily)
            additional_star = max(0, additional_star)
            star_daily += additional_star
            remaining_capacity = max(0, remaining_capacity_after_daily - additional_star)
            additional_grinding = min(remaining['total_grinding_remaining_duration'] - grinding_daily, remaining_grinding_max, remaining_capacity)
            additional_grinding = max(0, additional_grinding)
            grinding_daily += additional_grinding
    elif has_both:
        # Default: Balanced completion - proportional allocation by remaining duration
        # This achieves "total income maximization" by finishing all goals as soon as possible
        # With daily tasks: start from daily requirements then allocate remaining proportional
        grinding_daily = daily_required_grinding
        star_daily = daily_required_star
        total_remaining_minutes = remaining['total_grinding_remaining_duration'] + remaining['total_star_remaining_duration']

        if total_remaining_minutes > 0 and remaining_capacity_after_daily > 0:
            # Proportional allocation for remaining capacity among REMAINING goal duration
            # available_remaining = remaining_capacity_after_daily (already subtracted daily)
            additional_grinding = (remaining['total_grinding_remaining_duration'] / total_remaining_minutes) * remaining_capacity_after_daily
            additional_star = (remaining['total_star_remaining_duration'] / total_remaining_minutes) * remaining_capacity_after_daily

            grinding_daily += additional_grinding
            star_daily += additional_star

        # Cannot exceed maximum concurrent slots for either activity
        # Daily already clamped, so just check for overflow after adding additional
        grinding_was_truncated = False
        star_was_truncated = False

        original_grinding = grinding_daily
        original_star = star_daily

        grinding_daily = min(grinding_daily, max_grinding_total)
        grinding_daily = max(0, grinding_daily)
        if grinding_daily < original_grinding - 1e-9:
            grinding_was_truncated = True

        star_daily = min(star_daily, max_star_total)
        star_daily = max(0, star_daily)
        if star_daily < original_star - 1e-9:
            star_was_truncated = True

        # If either hit max capacity, allocate remaining capacity to the other
        if grinding_was_truncated and not star_was_truncated:
            # Grinding hit max, give all remaining capacity to star
            remaining_capacity = max(0, (max_grinding_total + max_star_total) - grinding_daily)
            star_daily = min(remaining['total_star_remaining_duration'], remaining_capacity, max_star_total)
        elif star_was_truncated and not grinding_was_truncated:
            # Star hit max, give all remaining capacity to grinding
            remaining_capacity = max(0, (max_grinding_total + max_star_total) - star_daily)
            grinding_daily = min(remaining['total_grinding_remaining_duration'], remaining_capacity, max_grinding_total)
        # If both hit max or neither hit, keep original allocation
        # Both can only hit max when sum of max already <= total_daily_capacity, so it's fine

        # Final clamping
        grinding_daily = max(0, grinding_daily)
        star_daily = max(0, star_daily)
    elif remaining['total_grinding_remaining_value'] > 0:
        # Only grinding, use all grinding concurrent slots (capped by actual characters)
        # Start with daily requirements
        # Already calculated actual_max_grinding_slots above
        total_available_grinding = total_available_minutes * actual_max_grinding_slots
        # Already allocated daily requirements, add remaining
        remaining_for_goal = max(0, total_available_grinding - daily_required_grinding)
        remaining_goal_duration = max(0, remaining['total_grinding_remaining_duration'] - daily_required_grinding)
        additional = min(remaining_for_goal, remaining_goal_duration)
        grinding_daily = daily_required_grinding + additional
        grinding_daily = max(0, grinding_daily)
        star_daily = daily_required_star
        star_daily = max(0, star_daily)
    else:
        # Only star waiting, use all star waiting concurrent slots (capped by actual characters)
        # Start with daily requirements
        # Already calculated actual_max_star_slots above
        total_available_star = total_available_minutes * actual_max_star_slots
        # Already allocated daily requirements, add remaining
        remaining_for_goal = max(0, total_available_star - daily_required_star)
        remaining_goal_duration = max(0, remaining['total_star_remaining_duration'] - daily_required_star)
        additional = min(remaining_for_goal, remaining_goal_duration)
        star_daily = daily_required_star + additional
        star_daily = max(0, star_daily)
        grinding_daily = daily_required_grinding
        grinding_daily = max(0, grinding_daily)

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

    # Generate recommendation with per-character details - all constraint enforcement happens inside generate_recommendation
    recommendation_text, recommendation_list = generate_recommendation(
        characters,
        grinding_daily, star_daily, estimated_days, estimated_income,
        remaining['total_grinding_remaining_value'], remaining['total_star_remaining_value'],
        daily_required_by_char,
        daily_tasks,
        settings.daily_total_hours
    )

    # Add daily tasks note at the beginning if we have daily tasks
    if daily_tasks and any(t.enabled for t in daily_tasks):
        enabled_tasks = [t for t in daily_tasks if t.enabled]
        daily_note = f"📋 每日任务优先分配\n已优先保证 {len(enabled_tasks)} 个每日任务的时长要求\n\n"
        recommendation_text = daily_note + recommendation_text

    return ActivitySuggestion(
        daily_grinding_minutes=grinding_daily,
        daily_star_waiting_minutes=star_daily,
        estimated_days_remaining=estimated_days,
        estimated_total_income=estimated_income,
        recommendation=recommendation_text,
        recommendation_list=recommendation_list
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
    daily_required_by_char: dict[str, dict[ActivityType, int]] = None,
    daily_tasks: Optional[List[DailyTask]] = None,
    daily_total_hours: float = 8.0,
) -> tuple[str, list['CharacterRecommendation']]:
    """Generate human readable recommendation with per-character details
    Returns both the text string for display and the structured list for GUI table
    """
    from src.core.models import CharacterRecommendation
    parts = []
    recommendation_list = []

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

        # 每个角色的每日日历时间限制：同一个角色一天不能超过这个时间
        daily_limit = daily_total_hours * 60
        # print(f"[DEBUG] daily_limit per character = {daily_limit:.0f} minutes")

        # ===========================================================================
        # 简单直接分配算法 - 绝对保证约束满足，不会出问题
        # 思路：先分配每日任务，再分配剩余容量，天然满足所有约束
        #
        # 步骤：
        # 1. 第一步：分配所有每日任务必须的时间（硬约束）
        # 2. 第二步：对每个角色，计算还剩多少可用容量 = daily_limit - (req_g + req_s)
        # 3. 第三步：计算全局还剩多少需要分配 = target_g - sum(req_g), target_s - sum(req_s)
        # 4. 第四步：每个角色按可用容量比例分配全局剩余的搬砖和蹲星总容量
        # 5. 第五步：每个角色在自己剩余容量内，按剩余目标比例分配搬砖和蹲星
        #
        # 这个方法保证：g + s = req_g + req_s + additional ≤ daily_limit，永远不超！
        # ===========================================================================

        # 第一步：分配每日任务，计算每个角色基础信息
        allocs = []
        total_req_g = 0.0
        total_req_s = 0.0
        total_remaining_capacity = 0.0

        for char in active_characters:
            _, total_g_dur, rem_g_val = char.calculate_totals(ActivityType.GRINDING)
            _, total_s_dur, rem_s_val = char.calculate_totals(ActivityType.STAR_WAITING)

            rem_g = max(0, char.grinding_goal.target_duration - total_g_dur) if char.grinding_goal else 0.0
            rem_s = max(0, char.star_waiting_goal.target_duration - total_s_dur) if char.star_waiting_goal else 0.0

            # 每日任务要求
            req_g = 0.0
            req_s = 0.0
            if daily_required_by_char and char.name in daily_required_by_char:
                req_g = float(daily_required_by_char[char.name][ActivityType.GRINDING])
                req_s = float(daily_required_by_char[char.name][ActivityType.STAR_WAITING])

            # 已经分配了每日任务
            g = req_g
            s = req_s

            # 计算该角色还剩多少容量可以分配给额外目标
            remaining_cap = max(0.0, daily_limit - (req_g + req_s))

            # 累加
            total_req_g += req_g
            total_req_s += req_s
            total_remaining_capacity += remaining_cap

            # 存储
            allocs.append({
                'char': char,
                'g': g,
                's': s,
                'req_g': req_g,
                'req_s': req_s,
                'rem_g': rem_g,
                'rem_s': rem_s,
                'remaining_capacity': remaining_cap,
                'max_g': req_g + rem_g,
                'max_s': req_s + rem_s,
                'daily_limit': daily_limit,
                'total_g_dur': total_g_dur,
                'total_s_dur': total_s_dur,
                'rem_g_val': rem_g_val,
                'rem_s_val': rem_s_val,
            })
            # print(f"[DEBUG] Step 1 {char.name}: req_g={req_g:.0f}, req_s={req_s:.0f}, remaining_cap={remaining_cap:.0f}")

        # print(f"[DEBUG] After step 1: total_req_g={total_req_g:.1f}, total_req_s={total_req_s:.1f}, total_remaining_capacity={total_remaining_capacity:.1f}")

        # 第三步：计算全局还需要分配多少
        remaining_global_g = max(0.0, grinding_daily - total_req_g)
        remaining_global_s = max(0.0, star_daily - total_req_s)
        # print(f"[DEBUG] Global remaining: G={remaining_global_g:.1f}, S={remaining_global_s:.1f}")

        # 第四步：分配剩余全局容量到各个角色，按剩余容量比例分配
        if total_remaining_capacity > 1e-9 and (remaining_global_g > 1e-9 or remaining_global_s > 1e-9):
            for alloc in allocs:
                if alloc['remaining_capacity'] <= 0:
                    continue

                # 该角色占总剩余容量的比例
                proportion = alloc['remaining_capacity'] / total_remaining_capacity

                # 按比例分配额外容量
                extra_g = proportion * remaining_global_g
                extra_s = proportion * remaining_global_s

                # 但不能超过该角色的剩余目标
                extra_g = min(extra_g, alloc['rem_g'])
                extra_s = min(extra_s, alloc['rem_s'])

                # 【关键】检查不超过剩余容量，总extra不能超过remaining_capacity
                total_extra = extra_g + extra_s
                if total_extra > alloc['remaining_capacity'] + 1e-9:
                    # 如果超了，按比例压缩，保证总和不超
                    if total_extra > 1e-9:
                        scale = alloc['remaining_capacity'] / total_extra
                        extra_g *= scale
                        extra_s *= scale
                    else:
                        extra_g = 0
                        extra_s = 0

                # 分配
                alloc['g'] += extra_g
                alloc['s'] += extra_s

                # print(f"[DEBUG] Step 4 {alloc['char'].name}: +g={extra_g:.1f}, +s={extra_s:.1f}, total={alloc['g']+alloc['s']:.0f}")

        # 第五步：最终保证 - 算法天然满足，这里只是保险
        # print(f"[DEBUG] Final guarantee:")
        for alloc in allocs:
            # 保证不超过上限（不能超过剩余目标）
            alloc['g'] = min(alloc['g'], alloc['max_g'])
            alloc['s'] = min(alloc['s'], alloc['max_s'])
            # 保证不超过总容量（算法天然保证，这里只是保险）
            if alloc['g'] + alloc['s'] > daily_limit + 1e-9:
                excess = alloc['g'] + alloc['s'] - daily_limit
                can_reduce_g = alloc['g'] - alloc['req_g']
                can_reduce_s = alloc['s'] - alloc['req_s']
                total_can = can_reduce_g + can_reduce_s
                if total_can > 1e-9:
                    scale = (total_can - excess) / total_can
                    alloc['g'] = alloc['req_g'] + can_reduce_g * scale
                    alloc['s'] = alloc['req_s'] + can_reduce_s * scale

        # 最终验证
        # print(f"[DEBUG] === FINAL VERIFICATION ====")
        # for alloc in allocs:
        #     total = alloc['g'] + alloc['s']
        #     ok = total <= daily_limit + 1e-9
        #     print(f"[DEBUG] {alloc['char'].name}: g={alloc['g']:.0f}, s={alloc['s']:.0f}, sum={total:.0f}, limit={daily_limit:.0f}, OK={ok}")

        # 构建表格，使用最终结果
        # print(f"[DEBUG] === Final allocations after all constraints: ===")
        # for alloc in allocs:
        #     char = alloc['char']
        #     char_g_daily = alloc['g']
        #     char_s_daily = alloc['s']
        #     total_g_duration = alloc['total_g_dur']
        #     total_s_duration = alloc['total_s_dur']
        #     remaining_g_value = alloc['rem_g_val']
        #     remaining_s_value = alloc['rem_s_val']

        #     print(f"[DEBUG] Final {char.name}: g={char_g_daily:.0f}, s={char_s_daily:.0f}, sum={char_g_daily+char_s_daily:.0f}")

            # Skip if no activity after projection
            if char_g_daily <= 0.1 and char_s_daily <= 0.1:
                continue

            # If this character has daily tasks, adjust the remaining duration calculation
            # daily tasks are already included in char_g_daily and char_s_daily
            if daily_required_by_char and char.name in daily_required_by_char:
                # Already accounted for in the allocation, no adjustment needed
                pass

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

            # Add to structured list for GUI table
            remaining_total_duration = 0
            if char.grinding_goal:
                remaining_total_duration += max(0, char.grinding_goal.target_duration - total_g_duration)
            if char.star_waiting_goal:
                remaining_total_duration += max(0, char.star_waiting_goal.target_duration - total_s_duration)

            recommendation_list.append(CharacterRecommendation(
                character_name=char.name,
                grinding_minutes=char_g_daily,
                star_waiting_minutes=char_s_daily,
                remaining_value=remaining_value,
                remaining_duration=remaining_total_duration,
                estimated_days=char_remaining_duration
            ))

            # Format table row for text output
            g_daily_str = f"{char_g_daily:.0f}'" if char_g_daily > 0.1 else "-"
            s_daily_str = f"{char_s_daily:.0f}'" if char_s_daily > 0.1 else "-"
            rv_str = f"{remaining_value:,}" if remaining_value > 0 else "-"

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

    return "".join(parts), recommendation_list
