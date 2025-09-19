from typing import Any, List, Dict, Union
import matplotlib.pyplot as plt
import numpy as np

PRINT_ERRORS = False

def print_errors(values, labels):
    if not PRINT_ERRORS:
        return

    if (
        not isinstance(values, dict)
        or not values
        or not isinstance(values[next(iter(values))], dict)
    ):
        return

    for label in labels:
        allv = {k: v.get(label, 0) for k, v in values.items()}
        print(f"{label}: {allv}")

def output_csv(result: Dict[str, Dict[str, float]]):
    keys = consolidate_keys(result, missing_ok=True)
    print("Label," + ",".join(result.keys()))
    for key in keys:
        values = [str(result[k].get(key, 0)) for k in result.keys()]
        print(f"{key}," + ",".join(values))

def consolidate_keys(data: Union[List[dict], Dict[Any, dict]], missing_ok=False):
    allkeys = list()

    alldicts = data if isinstance(data, list) else list(data.values())
    if not alldicts:
        return allkeys

    first = alldicts[0]
    assert all(isinstance(first, dict) == isinstance(d, dict) for d in alldicts), (
        "All values must be dictionaries or all values must not be dictionaries. "
        "Got a mix of dictionaries and non-dictionaries."
    )

    if not isinstance(first, dict):
        return [""]

    for d in alldicts:
        allkeys.extend([k for k in d.keys() if k not in allkeys])

    if not missing_ok:
        for d in alldicts:
            for k in allkeys:
                if k not in d:
                    raise ValueError(
                        f"Key {k} missing from dictionary. All keys: {allkeys}. "
                        f"Dictionary keys: {d.keys()}."
                    )
    return allkeys


def bar_side_by_side(
    result: Dict[str, Dict[str, float]],
    xlabel: str = None,
    ylabel: str = None,
    title: str = None,
    ax=None,
    missing_ok=False,
    legend_loc=None,
    legend_ncol=1,
    print_csv=False,
    yscale: str = "linear", 
    label_bars = True, 
    legend_off = False
):
    ax_provided = ax is not None
    _, ax = plt.subplots() if ax is None else (None, ax)

    keys = consolidate_keys(result, missing_ok=True)

    width = 1/(len(keys) + 1)
    x = np.arange(len(result))

    print_errors(result, keys)
    if print_csv:
        print(f'\n{xlabel} vs. {ylabel}')
        output_csv(result)
    
    for i, key in enumerate(keys):
        rects = ax.bar(
            x + i * width,
            [r[key] if key in r.keys() else 0 for r in result.values()],
            width,
            label=key,
        )
        if label_bars:
            ax.bar_label(rects, padding=3, fmt='%0.1e', rotation=90, label_type='center')
    
    # add labels for total in each group
    if label_bars:
        for i, group in enumerate(result.keys()):
            total = sum(result[group].values())
            max_height = max(result[group].values())
            ax.text(i+width, max_height*1.5, "%0.2e" % total, ha='center', fontweight='bold')

    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.set_xticks(x + (len(keys)*width/2) - width/2)
    ax.set_xticklabels(result.keys(), rotation=90)
    #ax.set_ylim(top=)
    ax.set_yscale(yscale)
    if len(consolidate_keys(result, missing_ok=missing_ok)) > 1 and not legend_off:
        ax.legend(loc=legend_loc, ncol=legend_ncol)
    if not ax_provided:
        plt.show()


def bar_stacked(
    result: Dict[str, Dict[str, float]],
    xlabel: str = None,
    ylabel: str = None,
    title: str = None,
    ax=None,
    missing_ok=False,
    legend_loc=None,
    print_csv=False,
    yscale: str = "linear"
):
    first_result = next(iter(result.values()))
    if isinstance(first_result, dict):
        assert all(
            isinstance(v, dict) for v in result.values()
        ), "All values must be dictionaries if the first value is a dictionary."
    else:
        result = {k: {"": v} for k, v in result.items()}

    ax_provided = ax is not None
    _, ax = plt.subplots() if ax is None else (None, ax)
    x = np.arange(len(result))
    width = 0.35
    bottom = np.zeros(len(result))  # Initialize the bottom array with zeros

    print_errors(result, consolidate_keys(result, missing_ok=True))
    if print_csv:
        print(f'\n{xlabel} vs. {ylabel}')
        output_csv(result)

    for component in consolidate_keys(result, missing_ok=missing_ok):
        values = [components.get(component, 0) for components in result.values()]
        ax.bar(x, values, width, label=component, bottom=bottom)
        bottom += values

    ax.set_yscale(yscale)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(result.keys(), rotation=90)
    ax.set_ylim(bottom=0)
    if len(consolidate_keys(result, missing_ok=missing_ok)) > 1:
        ax.legend(loc=legend_loc)
    if not ax_provided:
        plt.show()

def plot(
    result: Union[Dict[str, Dict[str, float]], Dict[str, float]],
    xlabel: str = None,
    ylabel: str = None,
    title: str = None,
    ax=None,
    missing_ok=True,
    legend_loc=None,
    print_csv=False,
):
    first_result = next(iter(result.values()))
    if isinstance(first_result, dict):
        assert all(
            isinstance(v, dict) for v in result.values()
        ), "All values must be dictionaries if the first value is a dictionary."
    else:
        result = {k: {"": v} for k, v in result.items()}

    keys = consolidate_keys(result, missing_ok=missing_ok)

    print_errors(result, keys)
    if print_csv:
        print(f'\n{xlabel} vs. {ylabel}')
        output_csv(result)

    ax_provided = ax is not None
    _, ax = plt.subplots() if ax is None else (None, ax)

    for key in keys:
        x = list(result.keys())
        y = [r[key] for r in result.values()]
        x, y = zip(*((x, y) for x, y in zip(x, y) if x is not None and y is not None))
        ax.plot(x, y, label=key)
    ax.set_xticks(x)
    ax.set_xticklabels(x, rotation=90)  # TODO FIX ME
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.set_ylim(bottom=0)
    if len(keys) > 1:
        ax.legend(loc=legend_loc)
    if not ax_provided:
        plt.show()

def scatter(
    result: Union[Dict[str, Dict[str, float]], Dict[str, float]],
    xlabel: str = None,
    ylabel: str = None,
    title: str = None,
    ax=None,
    missing_ok=True,
    legend_loc=None,
    print_csv=False,
):
    first_result = next(iter(result.values()))
    if isinstance(first_result, dict):
        assert all(
            isinstance(v, dict) for v in result.values()
        ), "All values must be dictionaries if the first value is a dictionary."
    else:
        result = {k: {"": v} for k, v in result.items()}

    keys = consolidate_keys(result, missing_ok=missing_ok)

    print_errors(result, keys)
    if print_csv:
        print(f'\n{xlabel} vs. {ylabel}')
        output_csv(result)

    ax_provided = ax is not None
    _, ax = plt.subplots() if ax is None else (None, ax)

    for key in keys:
        x = list(result.keys())
        y = [r[key] for r in result.values()]
        x, y = zip(*((x, y) for x, y in zip(x, y) if x is not None and y is not None))
        ax.scatter(x, y, label=key)
    # ax.set_xticklabels(ax.get_xticks(), rotation=90) TODO FIX ME
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.set_ylim(bottom=0)
    if len(keys) > 1:
        ax.legend(loc=legend_loc)
    if not ax_provided:
        plt.show()