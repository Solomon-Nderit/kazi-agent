from pathlib import Path

import mss


def on_exists(fname: str) -> None:
    """Callback example when we try to overwrite an existing screenshot."""
    file = Path(fname)
    if file.is_file():
        newfile = file.with_name(f"{file.name}.old")
        print(f"{fname} → {newfile}")
        file.rename(newfile)


with mss.mss() as sct:
    filename = sct.shot(output="mon-{mon}.png", callback=on_exists)
    print(filename)