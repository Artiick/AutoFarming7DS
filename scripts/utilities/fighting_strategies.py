"""This script implements different fighting logics/strategies.
VERY IMPORTANT: They should be independent from the activity they are used on"""

import abc
from copy import deepcopy
from numbers import Integral

import numpy as np
from termcolor import cprint
from utilities.battle_utilities import (
    pick_card_type,
    process_card_move,
    process_card_play,
)
from utilities.card_data import Card, CardTypes
from utilities.utilities import get_hand_cards


class IBattleStrategy(abc.ABC):
    """Interface that groups all battle fighting strategies"""

    def pick_cards(self, *args, **kwargs) -> tuple[list[Card], list[int]]:
        """*args and **kwargs just for compatibility across classes and subclasses. Probably not the best coding..."""

        # Extract the cards
        hand_of_cards: list[Card] = get_hand_cards()
        original_hand_of_cards = deepcopy(hand_of_cards)

        card_indices = []
        picked_cards = []
        for _ in range(8):

            # Extract the next index to click on
            next_index = self.get_next_card_index(hand_of_cards, picked_cards)

            # Update the indices and cards lists
            card_indices.append(next_index)
            picked_cards.append(hand_of_cards[next_index])

            # Update the cards list
            hand_of_cards = self._update_hand_of_cards(hand_of_cards, [next_index])

        return original_hand_of_cards, card_indices

    def _update_hand_of_cards(self, house_of_cards: list[Card], indices: list[int]) -> list[Card]:
        """Given the selected indices, select the cards accounting for card shifts.

        Args:
            house_of_cards (list[Card]): List of the cards in hand before any is played.
            indices (list[int]): Original cards we want to play.
                                  The indices will have to be modified accounting for shifts and merges RECURSIVELY.
        """

        for idx in indices:
            if isinstance(idx, Integral):
                # We're playing a card
                process_card_play(house_of_cards, idx)

            elif isinstance(idx, (tuple, list)):
                # We're moving a card
                process_card_move(house_of_cards, idx[0], idx[1])

            else:
                raise ValueError(f"Index {idx} is neither an integer nor a list/tuple!")

        # Finally, return the new card array and indices modified
        return house_of_cards

    @abc.abstractmethod
    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Return the indices for the cards to use in order, based on the current 'state'.
        NOTE: This method needs to be implemented by a subclass.
        """


class DummyBattleStrategy(IBattleStrategy):
    """Always pick the rightmost four cards, regardless of what they are"""

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Always get the rightmost 4 cards"""
        return 7


class SmarterBattleStrategy(IBattleStrategy):
    """This strategy assumes the card types can be read properly.
    It prioritizes one recovery and one stance card, and then it picks attack cards for the remaining slots."""

    @classmethod
    def get_next_card_index(cls, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """Apply the logic to extract the right indices.
        NOTE: Add attack-debuff cards too."""

        # Extract the card types and ranks, and reverse the list to give higher priority to rightmost cards (to maximize card rotation)
        card_types = np.array([card.card_type.value for card in hand_of_cards])
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])
        picked_card_types = np.array([card.card_type.value for card in picked_cards])

        # Keep track of all the indices
        all_indices = np.arange(len(hand_of_cards))

        # ULTIMATE CARDS
        ult_ids = np.where(card_types == CardTypes.ULTIMATE.value)[0]
        if ult_ids.size:
            return ult_ids[-1]

        # RECOVERY CARDS
        recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
        if recovery_ids.size and not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size:
            return recovery_ids[-1]

        # STANCE CARDS -- Use it if there's no recovery card
        stance_ids = np.where(card_types == CardTypes.STANCE.value)[0]
        if (
            stance_ids.size
            and not np.where(picked_card_types == CardTypes.STANCE.value)[0].size
            and not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size
        ):
            return stance_ids[-1]

        # FIRST ATATCK-DEBUFF CARDS
        att_debuff_ids = np.where(card_types == CardTypes.ATTACK_DEBUFF.value)[0]
        # Sort them based on card ranks
        att_debuff_ids: np.ndarray = np.array(sorted(att_debuff_ids, key=lambda idx: card_ranks[idx], reverse=False))
        if att_debuff_ids.size and not np.where(picked_card_types == CardTypes)[0].size:
            return att_debuff_ids[-1]

        # ATTACK CARDS
        attack_ids = np.where(card_types == CardTypes.ATTACK.value)[0]
        # Lets sort the attack cards based on their rank
        attack_ids = sorted(attack_ids, key=lambda idx: card_ranks[idx], reverse=False)
        if len(attack_ids):
            return attack_ids[-1]

        # CONSIDER THE REMAINING CARDS
        # Append the rest together: Ultimates, 1 recovery, 1 stance, 1 attack-debuff, all attacks, all attack-debuffs, the rest
        selected_ids = np.hstack((stance_ids, recovery_ids, att_debuff_ids))

        # Let's extract the DISABLED and GROUND cards too, to append them at the very end
        disabled_ids = np.where(card_types == CardTypes.DISABLED.value)[0]
        ground_ids = np.where(card_types == CardTypes.GROUND.value)[0]

        # Find the remaining cards (without considering the disabled/ground cards), and append them at the end
        remaining_indices = np.setdiff1d(all_indices, np.hstack((ground_ids, disabled_ids, selected_ids)))

        # Concatenate the selected IDs, with the remaining IDs, and at the very end, the disabled IDs.
        final_indices = np.hstack((disabled_ids, remaining_indices, selected_ids)).astype(int)

        # Return the next index!
        return final_indices[-1]


class Floor4BattleStrategy(IBattleStrategy):
    """The logic behind the battle for FLoor 4"""

    def pick_cards(self, phase) -> tuple[list[Card], list[int]]:
        """*args and **kwargs just for compatibility across classes and subclasses. Probably not the best coding..."""

        # Extract the cards
        hand_of_cards: list[Card] = get_hand_cards()

        card_indices = []
        picked_cards = []
        for _ in range(7):
            # Extract the next index to click on
            next_index = self.get_next_card_index(hand_of_cards, picked_cards, phase=phase)
            card_indices.append(next_index)
            picked_cards.append(hand_of_cards[next_index])

            # Update the cards list
            hand_of_cards, _ = self._update_hand_of_cards(hand_of_cards, [next_index])

        return picked_cards, card_indices

    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], phase: int) -> int:
        """Extract the indices based on the list of cards and the current bird phase"""
        if phase == 1:
            card_index = self.get_next_card_index_phase1(hand_of_cards, picked_cards)
        elif phase == 2:
            card_index = self.get_next_card_index_phase2(hand_of_cards, picked_cards)
        elif phase == 3:
            card_index = self.get_next_card_index_phase3(hand_of_cards, picked_cards)
        elif phase == 4:
            card_index = self.get_next_card_index_phase4(hand_of_cards, picked_cards)

        return card_index

    def get_next_card_index_phase1(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """The logic for phase 1... use the existing smarter strategy"""
        # SmarterBattleStrategy.get_next_card_index(hand_of_cards)

        # To start testing, let's just move cards
        return [[0, 7], [1, 6], [2, 5], [3, 4]]

    def get_next_card_index_phase2(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """The logic for phase 1... use the existing smarter strategy"""
        SmarterBattleStrategy.get_next_card_index(hand_of_cards)

    def get_next_card_index_phase3(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """The logic for phase 1... use the existing smarter strategy"""
        SmarterBattleStrategy.get_next_card_index(hand_of_cards)

    def get_next_card_index_phase4(self, hand_of_cards: list[Card], picked_cards: list[Card]) -> int:
        """The logic for phase 1... use the existing smarter strategy"""
        SmarterBattleStrategy.get_next_card_index(hand_of_cards)
