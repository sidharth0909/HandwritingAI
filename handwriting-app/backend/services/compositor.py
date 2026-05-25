from PIL import Image, ImageDraw, ImageFont


def _add_watermark(page: Image.Image) -> Image.Image:
    draw = ImageDraw.Draw(page)
    text = "HandwritingAI · github.com/sidharth0909"
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = (page.width - text_w) // 2
    y = page.height - 120
    draw.text((x, y), text, fill=(180, 180, 180), font=font)
    return page


def compose_page(
    word_images: list[Image.Image],
    page_width: int = 2480,
    page_height: int = 3508,
    margin: int = 200,
    line_spacing: int = 120,
    word_gap: int = 24,
) -> Image.Image:
    page = Image.new("RGB", (page_width, page_height), color=(255, 255, 255))

    if not word_images:
        return _add_watermark(page)

    max_x = page_width - margin
    lines: list[list[Image.Image]] = []
    current_line: list[Image.Image] = []
    x = margin

    for word_img in word_images:
        w, h = word_img.size
        if x + w > max_x and current_line:
            lines.append(current_line)
            current_line = [word_img]
            x = margin + w + word_gap
        else:
            current_line.append(word_img)
            x += w + word_gap

    if current_line:
        lines.append(current_line)

    y = margin
    for line in lines:
        line_h = max(img.size[1] for img in line)
        x = margin
        for word_img in line:
            w, h = word_img.size
            paste_y = y + (line_h - h)
            if paste_y + h > page_height - margin:
                break
            page.paste(word_img, (x, paste_y))
            x += w + word_gap
        y += line_h + line_spacing
        if y > page_height - margin:
            break

    page = _add_watermark(page)
    return page


def compose_pages(word_images: list[Image.Image], num_pages: int) -> list[Image.Image]:
    if not word_images:
        return [Image.new("RGB", (2480, 3508), color=(255, 255, 255)) for _ in range(num_pages)]

    per_page = max(1, len(word_images) // num_pages)
    pages: list[Image.Image] = []
    for i in range(num_pages):
        start = i * per_page
        end = (i + 1) * per_page if i < num_pages - 1 else len(word_images)
        chunk = word_images[start:end] if start < len(word_images) else word_images[-per_page:]
        if not chunk:
            chunk = word_images
        pages.append(compose_page(chunk))
    return pages
