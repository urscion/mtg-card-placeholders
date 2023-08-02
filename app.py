#!/usr/bin/env python3
import copy
import itertools
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List

import mtg_parser
import reportlab.lib.enums as rl_enums
import scrython.cards
import tyro
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

COLUMNS = 5
SPACER_SIZE = 0.20 * inch
MAX_NUMBER_OF_SETS = 10
PLACEHOLDER_STYLE = TableStyle(
    [
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
        ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
    ]
)


@dataclass
class Arguments:
    deck_path: str
    notes: str = ""


def create_table(deck: List[mtg_parser.Card]) -> Table:
    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    normal_style.fontName = "Courier"
    normal_style.alignment = rl_enums.TA_LEFT

    style_card = copy.deepcopy(styles["Normal"])
    style_card.fontSize = 20
    style_card.leading = 24

    style_info = copy.deepcopy(styles["Normal"])
    style_info.fontSize = 14
    style_info.leading = 16

    style_set = copy.deepcopy(styles["Normal"])
    style_set.fontSize = 8
    style_set.leading = 10

    style_notes = copy.deepcopy(styles["Normal"])
    style_notes.fontSize = 14
    style_notes.leading = 12

    data = []
    deck = sorted(deck, key=lambda x: x.name)
    card_chunks = [deck[i : i + COLUMNS] for i in range(0, len(deck), COLUMNS)]
    for card_chunk in card_chunks:
        row = []
        for card in card_chunk:
            print(card.name)
            search = scrython.cards.Search(
                q=f"name:{card.name}",
                unique="prints",
            )
            scry_cards = [d for d in search.data()]

            set_map = defaultdict(set)
            card_info = ""
            set_prices = {}
            set_rarities = {}
            for scry_card in scry_cards:
                if "paper" not in scry_card["games"]:
                    continue
                if not card_info:
                    colors = scry_card["colors"] if "colors" in scry_card else scry_card["card_faces"][0]["colors"]
                    colors = colors or "C"
                    card_colors = "/".join(colors)
                    card_info = f"Color: {card_colors}"
                set_code = scry_card["set"].upper()
                # Never going to collect these
                if set_code in ["LEA", "LEB", "SUM", "4BB", "FBB"] or len(set_code) != 3:
                    continue
                set_rarities[set_code] = scry_card["rarity"][0].upper()
                set_map[scry_card["set_type"]].add(f"{set_code}")
                try:
                    set_prices[set_code] = f"{float(scry_card['prices']['usd']):05.2f}"
                except Exception:
                    pass

            collect_sets = set_map["core"] | set_map["expansion"]
            commander_sets = set_map["commander"]

            # No collector sets and Commander sets exist
            if len(collect_sets) > MAX_NUMBER_OF_SETS:
                if len(commander_sets) <= MAX_NUMBER_OF_SETS:
                    set_of_sets = commander_sets
                set_of_sets = ["[ManySets]"]
            # Zero collector sets, use all sets instead
            elif len(collect_sets) == 0:
                set_of_sets = itertools.chain.from_iterable([sets for sets in set_map.values()])
            # Print found sets
            else:
                set_of_sets = collect_sets

            # Set info
            set_info = [
                f"{myset}[{set_rarities[myset]}]({set_prices.get(myset, '')})" if myset in set_rarities else myset
                for myset in sorted(set_of_sets)
            ]
            set_info_lines = [" ".join(set_info[i : i + 2]) for i in range(0, len(set_info), 2)]
            for _ in range(0, 5 - len(set_info_lines)):
                set_info_lines.append("&nbsp;")
            set_str = "<br/>".join(set_info_lines)
            set_str_with_padding = f"{set_str}".replace(" ", "&nbsp;")

            # Card name
            card_name = str(card.name).split("//")[0] + " [2]" if "//" in card.name else card.name
            card_name_with_padding = f"{card_name:50s}".replace(" ", "&nbsp;")

            cell = [
                Paragraph(f"{card_name_with_padding}", style=style_card),
                Paragraph(f"{card_info}", style=style_info),
                Paragraph(f"{set_str_with_padding}", style=style_set),
            ]
            if args.notes:
                cell.append(Paragraph(f"{args.notes}", style=style_notes))
            row.append(cell)
        data.append(row)

    card_print_size = (
        2.5 * inch - 2 * SPACER_SIZE,
        3.5 * inch - 2 * SPACER_SIZE,
    )
    return Table(
        data,
        colWidths=[card_print_size[0]] * COLUMNS,
        rowHeights=[card_print_size[1]] * len(card_chunks),
        style=PLACEHOLDER_STYLE,
    )


def main(args: Arguments) -> None:
    deck_path = Path(args.deck_path)
    deck: List[mtg_parser.Card] = list(mtg_parser.parse_deck(str(args.deck_path)))

    for card in deck:
        print(card)

    doc = SimpleDocTemplate("card-placeholders.pdf", pagesize=landscape(letter))
    t = create_table(deck)

    doc.build([t])


if __name__ == "__main__":
    args = tyro.cli(Arguments)
    main(args)
