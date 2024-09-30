import abc
from copy import deepcopy
from numbers import Integral

import numpy as np
import utilities.vision_images as vio
from termcolor import cprint
from utilities.battle_utilities import process_card_move, process_card_play
from utilities.card_data import Card, CardRanks, CardTypes
from utilities.fighting_strategies import IBattleStrategy, SmarterBattleStrategy
from utilities.logging_utils import LoggerWrapper
from utilities.utilities import (
    capture_window,
    count_immortality_buffs,
    determine_card_merge,
    display_image,
    find,
    get_hand_cards,
    is_amplify_card,
    is_ground_card,
    is_hard_hitting_card,
    is_hard_hitting_snake_card,
    is_Meli_card,
    is_stance_cancel_card,
    is_Thor_card,
)


class DogsBattleStrategy(IBattleStrategy):
    """The logic behind the AI for Snake"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], floor: int, phase: int) -> int:
        """Extract the next card index based on the hand and picked cards information,
        together with the current floor and phase.
        """

        if floor == 1 and phase == 2:
            return self.floor_1_phase_2(hand_of_cards, picked_cards)

        # Default
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)

    def floor_1_phase_2(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Keep at least 2 ultimates in hand!"""

        # Identify the IDs that contain an ultimate
        ult_ids = np.where([card.card_type == CardTypes.ULTIMATE for card in hand_of_cards])[0]

        # Disable the first 2 ultimates
        for i, id in enumerate(ult_ids):
            if i < 2:
                print("Disabling an ultimate!")
                hand_of_cards[id].card_type = CardTypes.DISABLED

        # Default to Smarter strategy
        return SmarterBattleStrategy.get_next_card_index(hand_of_cards, picked_cards)
