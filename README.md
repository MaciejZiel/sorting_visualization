# Neon Sorting Studio

Neon Sorting Studio is a polished desktop sorting visualizer built with Python and Pygame. It focuses on smooth bar motion, a clean dark neon aesthetic, and responsive controls for exploring classic sorting algorithms.

## Features

- Bubble Sort, Selection Sort, Insertion Sort, Merge Sort, and Quick Sort
- Smooth animated comparisons, swaps, overwrites, and finish-state highlighting
- On-screen controls plus keyboard shortcuts
- Automatic UI scaling on high-resolution displays, with manual UI scale controls
- Adjustable array size and animation speed
- Shuffle, reset, pause/resume, and single-step playback
- Live stats for comparisons, swaps, writes, elapsed time, status, and active algorithm

## Project Structure

```text
sorting_visualization/
├── main.py
├── requirements.txt
├── README.md
└── sorting_visualizer/
    ├── __init__.py
    ├── app.py
    ├── config.py
    ├── drawing.py
    ├── renderer.py
    ├── sorting.py
    └── ui.py
```

## Run

1. Create or activate a virtual environment.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Start the app:

```bash
python main.py
```

## Keyboard Shortcuts

- `Enter`: start sorting
- `Space`: pause or resume
- `N`: advance one step
- `R`: reset to the current shuffled array
- `H`: generate a new shuffled array
- `[` / `]`: decrease or increase array size
- `-` / `=`: slow down or speed up the animation
- `,` / `.`: decrease or increase UI scale
- `Left` / `Right`: cycle algorithms
- `1` to `5`: choose a specific algorithm
- `Esc`: quit

## Dependency List

- Python 3.11+
- `pygame`
