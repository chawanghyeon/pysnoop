# core/metrics/ascii_plot.py


def plot_ascii(values, width=60, height=10):
    if not values:
        print("[INFO] No data to plot.")
        return

    vals = [v for _, v in values]
    min_val, max_val = min(vals), max(vals)

    if min_val == max_val:
        min_val -= 1
        max_val += 1

    scaled = [int((v - min_val) / (max_val - min_val) * (height - 1)) for v in vals]

    grid = [[" " for _ in range(len(values))] for _ in range(height)]
    for i, y in enumerate(scaled):
        grid[height - y - 1][i] = "█"

    for row in grid:
        print("".join(row))

    print(f"min: {min_val:.2f}  max: {max_val:.2f}")
