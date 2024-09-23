"""This script implements different fighting logics/strategies.
VERY IMPORTANT: They should be independent from the activity they are used on"""

import abc
from copy import deepcopy
from numbers import Integral

import numpy as np
import utilities.vision_images as vio
from termcolor import cprint
from utilities.battle_utilities import process_card_move, process_card_play
from utilities.card_data import Card, CardRanks, CardTypes
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
    is_Meli_card,
    is_Thor_card,
)

logger = LoggerWrapper(name="FightingStrategies", log_file="fighter.log")


class IBattleStrategy(abc.ABC):
    """Interface that groups all battle fighting strategies"""

    card_turn = 0
    cards_to_play = 0

    def pick_cards(self, cards_to_play=4, **kwargs) -> tuple[list[Card], list[int]]:
        """**kwargs just for compatibility across classes and subclasses. Probably not the best coding..."""

        # Extract the cards
        hand_of_cards: list[Card] = get_hand_cards()
        original_hand_of_cards = deepcopy(hand_of_cards)

        print("Card types:", [card.card_type.name for card in hand_of_cards])
        print("Card ranks:", [card.card_rank.name for card in hand_of_cards])

        card_indices = []
        picked_cards = []

        # Extract how many cards we have to play
        IBattleStrategy.cards_to_play = cards_to_play

        # TODO: For now we need to hardcode the '4', otherwise code may break on line 82 of general_figher_interface.py...
        for _ in range(4):

            # Extract the next index to click on
            next_index = self.get_next_card_index(hand_of_cards, picked_cards, **kwargs)
            if isinstance(next_index, Integral):
                # Ensure we don't pick a GROUND card
                while (
                    next_index != -1
                    and next_index < len(hand_of_cards) - 1
                    and is_ground_card(hand_of_cards[next_index])
                ):
                    print(f"We can't pick card with index {next_index}, it's GROUND.")
                    next_index += 1

                print(f"Picked index {next_index} with card {hand_of_cards[next_index].card_type.name}")
                picked_cards.append(hand_of_cards[next_index])

            elif isinstance(next_index, (tuple, list)):
                print(f"Moving cards: {next_index}")

            # Update the indices and cards lists
            card_indices.append(next_index)

            # Update the cards list
            hand_of_cards = self._update_hand_of_cards(hand_of_cards, [next_index])

            # Increment the card turn
            IBattleStrategy.card_turn += 1

        IBattleStrategy.card_turn = 0
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
    def get_next_card_index(self, hand_of_cards: list[Card], picked_cards: list[Card], **kwargs) -> int:
        """Return the indices for the cards to use in order, based on the current 'state'.
        NOTE: This method needs to be implemented by a subclass.
        """


class DummyBattleStrategy(IBattleStrategy):
    """Always pick the rightmost four cards, regardless of what they are"""

    def get_next_card_index(self, *args, **kwargs) -> int:
        """Always get the rightmost card"""
        return -1


class SmarterBattleStrategy(IBattleStrategy):
    """This strategy assumes the card types can be read properly.
    It prioritizes one recovery and one stance card, and then it picks attack cards for the remaining slots."""

    @classmethod
    def get_next_card_index(cls, hand_of_cards: list[Card], picked_cards: list[Card], **kwargs) -> int:
        """Apply the logic to extract the right indices."""

        # Extract the card types and ranks, and reverse the list to give higher priority to rightmost cards (to maximize card rotation)
        card_types = np.array([card.card_type.value for card in hand_of_cards])
        card_ranks = np.array([card.card_rank.value for card in hand_of_cards])
        picked_card_types = np.array([card.card_type.value for card in picked_cards])

        # STANCE CARDS
        if (stance_idx := play_stance_card(card_types, picked_card_types)) is not None:
            return stance_idx

        # ULTIMATE CARDS
        ult_ids = np.where(card_types == CardTypes.ULTIMATE.value)[0]
        print("Picking ultimates?")
        if len(ult_ids):
            return ult_ids[-1]

        # RECOVERY CARDS
        recovery_ids = np.where(card_types == CardTypes.RECOVERY.value)[0]
        if (
            len(recovery_ids)
            and not np.where(picked_card_types == CardTypes.RECOVERY.value)[0].size
            and not np.where(picked_card_types == CardTypes.STANCE.value)[0].size
        ):
            return recovery_ids[-1]

        # BUFF CARDS
        buff_ids = sorted(np.where(card_types == CardTypes.BUFF.value)[0], key=lambda idx: card_ranks[idx])
        if len(buff_ids) and not np.where(picked_card_types == CardTypes.BUFF.value)[0].size:
            return buff_ids[-1]

        # CARD MERGE -- If there's a card that generates a merge (and not disabled), pick it!
        for i in range(1, len(hand_of_cards) - 1):
            if hand_of_cards[i].card_type != CardTypes.DISABLED and determine_card_merge(
                hand_of_cards[i - 1], hand_of_cards[i + 1]
            ):
                return i

        # FIRST ATATCK-DEBUFF CARD
        att_debuff_ids = np.where(card_types == CardTypes.ATTACK_DEBUFF.value)[0]
        # Sort them based on card ranks
        att_debuff_ids: np.ndarray = np.array(sorted(att_debuff_ids, key=lambda idx: card_ranks[idx], reverse=False))
        if att_debuff_ids.size and not np.where(picked_card_types == CardTypes.ATTACK_DEBUFF.value)[0].size:
            return att_debuff_ids[-1]

        # ATTACK CARDS
        attack_ids = np.where(card_types == CardTypes.ATTACK.value)[0]
        # Lets sort the attack cards based on their rank
        attack_ids = sorted(attack_ids, key=lambda idx: card_ranks[idx], reverse=False)
        if len(attack_ids):
            return attack_ids[-1]

        print("We don't meet any of the previous criteria, defaulting to the rightmost index")
        return -1


def play_stance_card(card_types: np.ndarray, picked_card_types: np.ndarray, card_ranks: np.ndarray = None):
    """Play a stance card if we have it and haven't played it yet"""
    screenshot, _ = capture_window()
    stance_ids = np.where(card_types == CardTypes.STANCE.value)[0]
    if card_ranks is not None:
        # Play higher ranked cards if possible
        stance_ids = sorted(stance_ids, key=lambda idx: card_ranks[idx], reverse=False)
    if (
        len(stance_ids)
        and not np.where(picked_card_types == CardTypes.STANCE.value)[0].size
        and not find(vio.stance_active, screenshot, threshold=0.5)
    ):
        print("We don't have a stance up, we need to enable it!")
        return stance_ids[-1]

    # If we don't find any stance
    return None
