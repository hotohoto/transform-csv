#! /usr/bin/env python

import argparse
import curses
import json
import pathlib
import typing as t
from dataclasses import dataclass

import pandas as pd

CACHE_PATH = pathlib.Path(pathlib.Path(__file__).parent, ".fields_setting.json")


@dataclass
class FieldsSetting:
    all_fields: t.List[str]
    fields_to_window: t.List[str]
    fields_to_drop: t.List[str]


def save_all_cache(all_cache):
    with open(CACHE_PATH, "w") as f:
        f.write(json.dumps(all_cache, indent=4, sort_keys=True))


def load_all_cache():
    if not CACHE_PATH.exists():
        return {}
    with open(
        CACHE_PATH,
    ) as f:
        return json.loads(f.read())


def save_fields_setting(input_file_path: pathlib.Path, fields_setting: FieldsSetting):
    def to_plain(self):
        return {
            "all_fields": self.all_fields,
            "fields_to_window": self.fields_to_window,
            "fields_to_drop": self.fields_to_drop,
        }

    input_file_path = input_file_path.resolve()
    key = str(input_file_path)
    all_cache = load_all_cache()
    all_cache[key] = to_plain(fields_setting)
    save_all_cache(all_cache)


def load_fields_setting(input_file_path: pathlib.Path) -> t.Union[None, FieldsSetting]:
    def from_plain(plain_obj):
        return FieldsSetting(
            all_fields=plain_obj["all_fields"],
            fields_to_window=plain_obj["fields_to_window"],
            fields_to_drop=plain_obj["fields_to_drop"],
        )

    input_file_path = input_file_path.resolve()
    key = str(input_file_path)
    all_cache = load_all_cache()

    if key in all_cache:
        return from_plain(all_cache[key])
    else:
        filename = input_file_path.name
        for k in all_cache:
            if k.endswith(filename):
                return from_plain(all_cache[k])
    return None


def configure_fields_settings_interactively(
    stdscr: "curses.window", fields_setting: FieldsSetting
) -> FieldsSetting:

    stdscr.clear()
    stdscr.refresh()

    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)

    COLOR_PAIR_CURRENT = curses.color_pair(1)
    COLOR_PAIR_DESCRIPTION = curses.color_pair(2)

    key = None
    current_field_idx = 0

    all_fields = fields_setting.all_fields
    fields_to_window = set(fields_setting.fields_to_window)
    fields_to_drop = set(fields_setting.fields_to_drop)
    fields_to_keep = set(fields_setting.all_fields) - fields_to_window - fields_to_drop

    GUIDE_TEXT = "Configure fields settings: [w] Window  [d] Drop  [k] Keep  [ENTER] Proceed  [q] Quit"

    pad_width = max(len(GUIDE_TEXT), max(len(f) for f in all_fields) + 4)
    pad_height = len(all_fields) + 2

    pad = curses.newpad(pad_height, pad_width)

    def go_down():
        nonlocal current_field_idx
        if current_field_idx < len(all_fields) - 1:
            current_field_idx += 1

    def go_up():
        nonlocal current_field_idx
        if current_field_idx > 0:
            current_field_idx -= 1

    while True:
        height, width = stdscr.getmaxyx()

        if key == curses.KEY_DOWN:
            go_down()
        elif key == curses.KEY_UP:
            go_up()
        elif key in {ord("k")} or key == ord(" "):
            current_field = all_fields[current_field_idx]
            fields_to_window.discard(current_field)
            fields_to_drop.discard(current_field)
            fields_to_keep.add(current_field)
            go_down()
        elif key == ord("d"):
            current_field = all_fields[current_field_idx]
            fields_to_window.discard(current_field)
            fields_to_drop.add(current_field)
            fields_to_keep.discard(current_field)
            go_down()
        elif key == ord("w"):
            current_field = all_fields[current_field_idx]
            fields_to_window.add(current_field)
            fields_to_drop.discard(current_field)
            fields_to_keep.discard(current_field)
            go_down()
        elif key == curses.KEY_ENTER or key == ord("\n"):
            break
        elif key == 27 or key == ord("q"):
            key = "Exit"
            exit()

        pad.attron(COLOR_PAIR_DESCRIPTION)
        pad.addstr(0, 0, GUIDE_TEXT)
        pad.attroff(COLOR_PAIR_DESCRIPTION)

        for i, field in enumerate(all_fields):
            current = i == current_field_idx
            if field in fields_to_window:
                flag = "w"
            elif field in fields_to_drop:
                flag = "d"
            elif field in fields_to_keep:
                flag = " "
            else:
                raise Exception(f"Unexpected field: {field}")

            if current:
                pad.attron(COLOR_PAIR_CURRENT)
            pad.addstr(i + 1, 0, f"[{flag}] {field}")
            if current:
                pad.attroff(COLOR_PAIR_CURRENT)

        # Refresh with scrolling
        pad.refresh(
            max(0, current_field_idx - height + 2),
            0,
            0,
            0,
            min(height, pad_height) - 1,
            min(width, pad_width) - 1,
        )

        # Wait for next input
        key = stdscr.getch()

    return FieldsSetting(all_fields, list(fields_to_window), list(fields_to_drop))


def path_with_suffix(suffix):
    def _type(s):
        path = pathlib.Path(s)
        if path.suffix.lower() == ".csv":
            return path
        raise argparse.ArgumentTypeError(f"{s} is not valid path for a {suffix} file")

    return _type


def positive_int(n):
    n = int(n)
    if n > 0 and n == float(n):
        return n
    raise argparse.ArgumentTypeError(f"{n} is not valid positive int")


def transform(
    df: pd.DataFrame, fields_setting: FieldsSetting, n_lags: int
) -> pd.DataFrame:
    _fields_to_window = set(fields_setting.fields_to_window)
    _fields_to_drop = set(fields_setting.fields_to_drop)

    df_new = pd.DataFrame(dtype=str)

    for f in fields_setting.all_fields:
        if f in _fields_to_window:
            for i in range(n_lags):
                new_field = f"{f}_T-{i}"
                df_new[new_field] = pd.Series([None] * i, dtype=str).append(
                    df[f][: len(df) - i], ignore_index=True
                )
        elif f in _fields_to_drop:
            continue
        else:
            df_new[f] = df[f]

    return df_new


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_file_path",
        help="path to the input CSV file",
        type=path_with_suffix(".csv"),
    )
    parser.add_argument(
        "output_file_path",
        help="path to the output CSV file",
        type=path_with_suffix(".csv"),
    )

    # TODO make this configurable using user inputs at runtime
    parser.add_argument(
        "n_lags",
        help="number of observed inputs required.",
        type=positive_int,
        default=1,
        nargs="?",
    )

    # TODO add the non interactive mode that will use the cached/default fields setting

    args = parser.parse_args()

    df = pd.read_csv(args.input_file_path, dtype=str)
    fields_setting = load_fields_setting(args.input_file_path)
    if not fields_setting:
        fields_setting = FieldsSetting(
            all_fields=list(df.columns), fields_to_window=[], fields_to_drop=[]
        )
    fields_setting = curses.wrapper(
        configure_fields_settings_interactively, fields_setting
    )
    save_fields_setting(args.input_file_path, fields_setting)
    df_new = transform(df, fields_setting, args.n_lags)
    df_new.to_csv(args.output_file_path, index=False)


if __name__ == "__main__":
    main()
