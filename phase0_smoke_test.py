#!/usr/bin/env python3
"""Smoke tests headless pour valider la Phase 0."""

from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys
from typing import Literal


Scenario = Literal["final_win", "game_over"]


def run_scenario(scenario: Scenario) -> str:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    import pygame  # import local après config SDL
    import levels

    if scenario == "final_win":
        for conf in levels.levels:
            conf["target_score"] = 0
    else:
        for conf in levels.levels:
            conf["target_score"] = 10**9

    # Accélère les transitions (warp/écrans) durant les tests.
    pygame.time.delay = lambda _ms: None  # type: ignore[assignment]

    state = {
        "frame": 0,
        "start_sent": False,
        "quit_sent": False,
        "boss_shot_sent": False,
    }

    def scripted_events():
        state["frame"] += 1
        if state["frame"] > 4000:
            raise RuntimeError(f"Timeout scenario={scenario}")

        module = sys.modules.get("main")
        game_state = getattr(module, "game_state", None)
        events = []

        if game_state == "MENU" and not state["start_sent"]:
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
            state["start_sent"] = True
        elif game_state == "LEVEL_INTRO":
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c))
        elif game_state == "BOSS_INTRO":
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c))
        elif (
            game_state == "PLAYING"
            and scenario == "final_win"
            and getattr(module, "boss_active", False)
            and not state["boss_shot_sent"]
        ):
            # Injecte un tir directement sur le boss pour forcer la victoire finale.
            boss = getattr(module, "boss_data", {})
            if boss:
                boss_rect = pygame.Rect(
                    int(boss["x"] + boss["width"] // 2),
                    int(boss["y"] + boss["height"] // 2),
                    4,
                    4,
                )
                module.boss_data["health"] = 1
                module.bullet_list.append({"rect": boss_rect, "dx": 0, "dy": 0})
                state["boss_shot_sent"] = True
        elif game_state == "PLAYING" and scenario == "game_over":
            # Force la transition GAME_OVER pour vérifier le flux.
            module.lives = 0
        elif game_state == "FINAL_WIN" and scenario == "final_win" and not state["quit_sent"]:
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q))
            state["quit_sent"] = True
        elif game_state == "GAME_OVER" and scenario == "game_over" and not state["quit_sent"]:
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q))
            state["quit_sent"] = True

        return events

    pygame.event.get = scripted_events  # type: ignore[assignment]

    original_exit = sys.exit
    sys.exit = lambda _code=0: None  # type: ignore[assignment]
    try:
        importlib.import_module("main")
    finally:
        sys.exit = original_exit

    module = sys.modules.get("main")
    return getattr(module, "game_state", "UNKNOWN")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["final_win", "game_over"])
    args = parser.parse_args()

    if args.scenario:
        result = run_scenario(args.scenario)  # run dans ce process
        print(f"SCENARIO={args.scenario}")
        print(f"SCENARIO_RESULT={result}")
        expected = "FINAL_WIN" if args.scenario == "final_win" else "GAME_OVER"
        print("SCENARIO_PASS" if result == expected else "SCENARIO_FAIL")
        return 0 if result == expected else 1

    # Lance chaque scénario dans un sous-processus pour isoler main.py (qui fait sys.exit()).
    final_proc = subprocess.run(
        [sys.executable, __file__, "--scenario", "final_win"],
        capture_output=True,
        text=True,
    )
    gameover_proc = subprocess.run(
        [sys.executable, __file__, "--scenario", "game_over"],
        capture_output=True,
        text=True,
    )

    final_ok = final_proc.returncode == 0
    gameover_ok = gameover_proc.returncode == 0

    print(final_proc.stdout.strip())
    print(gameover_proc.stdout.strip())
    if final_proc.stderr.strip():
        print(final_proc.stderr.strip())
    if gameover_proc.stderr.strip():
        print(gameover_proc.stderr.strip())

    ok = final_ok and gameover_ok
    print("PHASE0_SMOKE=PASS" if ok else "PHASE0_SMOKE=FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
