import argparse

from utilities.bird_floor4_fighting_strategies import BirdFloor4BattleStrategy
from utilities.bird_floor_4_farming_logic import BirdFloor4Farmer, States
from utilities.farming_factory import FarmingFactory


def main():

    # Extract the password if given
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", type=str, default=None, help="Account password")
    args = parser.parse_args()

    FarmingFactory.main_loop(
        farmer=BirdFloor4Farmer,
        battle_strategy=BirdFloor4BattleStrategy,  # The AI. Floor 4 requires a very specific logic
        starting_state=States.GOING_TO_DB,  # Should be 'GOING_TO_FLOOR' or 'FIGHTING', to start the script from outside or within the fight
        max_runs="inf",  # Can be a number or "inf"
        password=args.password,  # Account password
    )


if __name__ == "__main__":

    main()
