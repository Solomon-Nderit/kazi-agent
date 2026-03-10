from pathlib import Path

import mss


def on_exists(fname: str) -> None:
    """Callback example when we try to overwrite an existing screenshot."""
    file = Path(fname)
    if file.is_file():
        newfile = file.with_name(f"{file.name}.old")
        print(f"{fname} → {newfile}")
        file.rename(newfile)


def draw_grid_on_image(image_path, step_size, grid_color, output_path):
    """
    Draws a grid on an image using Pillow.

    Args:
        image_path (str): The path to the input image.
        step_size (int): The distance in pixels between grid lines.
        grid_color (tuple or str): The color of the grid lines (e.g., (128, 128, 128) for gray, or "red").
        output_path (str): The path to save the output image with the grid.
    """
    try:
        with Image.open(image_path) as image:
            draw = ImageDraw.Draw(image)
            width, height = image.size

            # Draw vertical lines
            for x in range(0, width, step_size):
                line = ((x, 0), (x, height))
                draw.line(line, fill=grid_color, width=1)

            # Draw horizontal lines
            for y in range(0, height, step_size):
                line = ((0, y), (width, y))
                draw.line(line, fill=grid_color, width=1)

            # Optional: remove the drawing object if not needed further
            del draw

            # Save the image
            image.save(output_path)
            # Display the image
            image.show()

    except IOError as e:
        print(f"Error opening or saving image: {e}")

# Example Usage:
# Replace 'input_image.jpg' with your image file path
# The step size is set to 50 pixels, and the color is set to a light gray
# The result will be saved as 'output_grid.jpg'


with mss.mss() as sct:
    filename = sct.shot(output="mon-{mon}.png", callback=on_exists)
    draw_grid_on_image('input_image.jpg', 50, (128, 128, 128), 'output_grid.jpg')
