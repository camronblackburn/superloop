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
    legend_off = False, 
    log_bottom = 1e-20, 
    total_label_multiplier = 1.1,
    gray_multiplier = 1.1
):
    ax_provided = ax is not None
    _, ax = plt.subplots() if ax is None else (None, ax)

    keys = consolidate_keys(result, missing_ok=True)

    print_errors(result, keys)
    if print_csv:
        print(f'\n{xlabel} vs. {ylabel}')
        output_csv(result)
    
    # For each group, find non-zero keys and calculate positions
    group_positions = []
    all_nonzero_keys = set()
    group_info = []  # Store info for background bars
    
    for group_idx, (group_name, group_data) in enumerate(result.items()):
        # Find non-zero keys for this group
        nonzero_keys = [key for key in keys if group_data.get(key, 0) > 0]
        all_nonzero_keys.update(nonzero_keys)
        
        if nonzero_keys:
            # Calculate width and positions for this group's bars
            n_bars = len(nonzero_keys)
            bar_width = 0.8 / max(len(keys), 1)  # Keep consistent width
            group_width = n_bars * bar_width
            group_center = group_idx
            start_pos = group_center - group_width / 2
            
            # Store group info for background bar
            max_height = max([group_data[key] for key in nonzero_keys])
            group_info.append((group_center, group_width, max_height))
            
            # Store positions for each bar in this group
            for i, key in enumerate(nonzero_keys):
                pos = start_pos + (i + 0.5) * bar_width
                group_positions.append((pos, group_data[key], key, group_idx))
    
    # Plot background bars for each group (low opacity)
    for group_center, group_width, max_height in group_info:
        ax.bar(group_center, max_height*gray_multiplier, width=group_width, 
               alpha=0.15, color='gray', zorder=0, edgecolor='none')
    
    # Plot bars at calculated positions
    bars_by_key = {}
    for pos, value, key, group_idx in group_positions:
        if key not in bars_by_key:
            bars_by_key[key] = ([], [])
        bars_by_key[key][0].append(pos)
        bars_by_key[key][1].append(value)
    
    # Plot each key's bars
    for key in all_nonzero_keys:
        if key in bars_by_key:
            positions, values = bars_by_key[key]
            rects = ax.bar(positions, values, width=0.8/max(len(keys), 1), label=key, zorder=2)
            if label_bars:
                # Use custom labeling to ensure labels don't go below visible area
                for rect in rects:
                    height = rect.get_height()
                    if height > 0:
                        # For both linear and log scale, position at middle of bar height
                        # The bar always starts from 0, so middle is height/2
                        label_y = (height * log_bottom) ** 0.5 if yscale == "log" else height / 2
                        #print(f"label_y before lim set: {label_y} for height {height}")
                        
                        # Ensure label doesn't go below the visible area
                        if yscale == "log":
                            # For log scale, respect the axis lower limit
                            y_min = max(ax.get_ylim()[0], 1e-20)
                            label_y = max(label_y, y_min)
                        else:
                            # For linear scale, don't go below 0
                            label_y = max(label_y, 0)
                        #print(f"label_y after lim set: {label_y} for height {height}")
                        
                        
                        ax.text(rect.get_x() + rect.get_width()/2, label_y,
                               f'{height:.1e}', ha='center', va='center', 
                               rotation=90, fontsize=8)
    
    # Add total labels for each group
    if label_bars:
        for group_idx, (group_name, group_data) in enumerate(result.items()):
            total = sum(v for v in group_data.values() if v > 0)
            if total > 0:
                max_height = max([v for v in group_data.values() if v > 0], default=0)
                if max_height > 0:
                    ax.text(group_idx, max_height*total_label_multiplier, "%0.2e" % total, 
                           ha='center', fontweight='bold')

    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.set_xticks(range(len(result)))
    ax.set_xticklabels(result.keys(), rotation=90)
    ax.set_yscale(yscale)
    if len(all_nonzero_keys) > 1 and not legend_off:
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