"""Typeset the locked 23 November 2026 edition of The World in One Day."""

import argparse
from dataclasses import dataclass
from functools import cache
from io import BytesIO
from itertools import combinations, pairwise
from math import dist
from pathlib import Path
import sys

try:
    from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
except ModuleNotFoundError as error:
    if error.name != "PIL":
        raise
    raise SystemExit(69) from error

PAGE = 1024
MARGIN, RIGHT = 28, PAGE - 28
DATE_MARGIN = 34
PAPER = "#F7F2E7"
INK = "#14213D"
RED = "#AF3427"
GOLD = "#E9C46A"
HAIRLINE = "#B6AA96"
SAND = "#EDE4D1"
MAP_BACKGROUND = "#F0EADB"
MAP_DOT = "#627183"
MAP_GRID = "#E0D7C4"

FONT_DIR = Path("/usr/share/fonts/truetype/liberation")
SANS_REGULAR = FONT_DIR / "LiberationSans-Regular.ttf"
SANS_BOLD = FONT_DIR / "LiberationSans-Bold.ttf"
NOTO_SERIF = Path.home() / ".local/share/fonts/NotoSerifJP.ttf"

MASTHEAD = "THE WORLD IN ONE DAY"
WEEKDAY, DATE = "Monday", "23 November 2026"
CLAIM_NOTE = "Ukrainian claim · Not independently confirmed"


@dataclass(frozen=True)
class Story:
    location: str
    headline: tuple[str, ...]
    body: str


STORIES = (
    Story(
        "Benghazi, Libya",
        ("UKRAINE SAYS ITS SEA", "DRONES STRUCK RUSSIAN", "SHIPS OFF LIBYA"),
        "Kyiv said seven unmanned boats struck the Benghazi naval base, destroying a Ka-27 helicopter "
        "and hitting the cargo ship MV Angara, as the corvette Merkury burned. "
        "President Zelensky claimed the operation; the UN urged a probe.",
    ),
    Story(
        "Kyiv, Ukraine",
        ("RUSSIAN STRIKES KILL", "AT LEAST 11 ACROSS THE", "KYIV REGION"),
        "The toll from Sunday's strikes rose as rescuers pulled bodies from the ruined apartment block in Dymer, "
        "where up to 11 people were feared buried; a supermarket in Vyshneve was also hit, killing two. "
        "The Kyiv region declared Monday a day of mourning.",
    ),
    Story(
        "Khartoum, Sudan",
        ("DRONES HIT HOMES AND A UN", "BUILDING IN KHARTOUM"),
        "Drone strikes on Sudan's capital killed four people and damaged a United Nations building; "
        "the paramilitary RSF was blamed for the attack.",
    ),
    Story(
        "Washington, United States",
        ("TRUMP DEFENDS FIRST TRILATERAL", "TALKS WITH XI AND PUTIN"),
        'The White House framed the first Xi-Trump-Putin trilateral meeting as necessary for "the safety of the world", '
        'and Trump again called Putin his "friend", as allies including Japan voiced unease at the summitry.',
    ),
    Story(
        "Seoul, South Korea",
        ("SEOUL NAMES NEW FOREIGN,", "UNIFICATION AND SPY CHIEFS"),
        "President Lee Jae Myung's reshuffle named a former justice minister as the country's first woman intelligence chief, "
        "a career diplomat as foreign minister, and a former lawmaker to lead unification policy toward North Korea.",
    ),
    Story(
        "Paris, France",
        ("FRANCE ARRESTS 144 IN", "COST-OF-LIVING PROTESTS"),
        "French police arrested 144 people in the latest weekend of cost-of-living protests, the interior ministry said, "
        "as the rallies entered a sixth weekend.",
    ),
    Story(
        "Jerusalem, Israel",
        ("NETANYAHU AND EISENKOT END", "TALKS WITHOUT A DEAL"),
        "Coalition talks between Benjamin Netanyahu's party and Gadi Eisenkot's ended without an agreement on forming "
        "a government, extending Israel's political deadlock as Eisenkot bids to topple the prime minister.",
    ),
    Story(
        "SPACE",
        ("BEPICOLOMBO SETTLES", "INTO ORBIT AROUND MERCURY"),
        "Eight years after launch, the joint ESA-JAXA probe BepiColombo is in orbit around Mercury, the least-explored "
        "planet in the inner solar system — a rare piece of good news, carried by Japan's space agency and Europe's alike.",
    ),
)

FIGURES = (
    "DEAD IN KYIV REGION STRIKES: 11+",
    "SEA DRONES OFF LIBYA: 7",
    "DEAD IN KHARTOUM STRIKES: 4",
    "ARRESTED IN FRANCE: 144",
    "YEARS TO MERCURY: 8",
)

TICKER = " • ".join((
    "Australia and Pacific nations despair at COP31 flop as backlash grows",
    "Trump 'inclined' to resume Iran strikes after New Year if no deal",
    "More remains found in Indonesia factory-fire search; 34 still missing",
    "Thousands evacuated from UK concert after unknown substance released",
    "Saudi Arabia intercepts drone and missile",
    "US probes Nvidia chip sales to China, Bessent says",
    "Thailand plans ban on chemical exports in pollution fight",
    "China sets 2030 targets for elderly care and childcare",
    "Onosato wins Kyushu sumo title, his seventh, in a playoff",
    "Alcaraz beats Zverev to win first ATP Finals title",
))

# Longitude, latitude, and the offset of the badge from that geographic anchor.
PINS = (
    (1, (20.0687, 32.1194), (-22, 30)),  # Benghazi
    (2, (30.5234, 50.4501), (18, -30)),  # Kyiv
    (3, (32.5599, 15.5007), (5, 35)),  # Khartoum
    (4, (-77.0369, 38.9072), (-9, 24)),  # Washington DC
    (5, (126.9780, 37.5665), (22, -24)),  # Seoul
    (6, (2.3522, 48.8566), (-26, -23)),  # Paris
    (7, (35.2137, 31.7683), (37, 13)),  # Jerusalem
)

# Use the series' simplified coastlines as the mask for the new dot grid.
COASTLINES = (
    (  # North America
        (-168, 65), (-162, 70), (-143, 71), (-133, 69), (-128, 72), (-111, 70),
        (-103, 74), (-88, 71), (-80, 74), (-69, 71), (-72, 65), (-87, 57),
        (-91, 61), (-97, 65), (-96, 54), (-85, 52), (-78, 57), (-77, 62),
        (-63, 58), (-60, 50), (-53, 49), (-66, 45), (-70, 42), (-74, 40.7),
        (-77, 35), (-81, 30), (-80, 25), (-84, 28), (-88, 30), (-96, 28),
        (-98, 22), (-92, 19), (-87, 21), (-86, 15), (-83, 9), (-78, 8),
        (-81, 8), (-88, 14), (-96, 16), (-104, 20), (-111, 28), (-115, 32),
        (-114, 26), (-121, 34), (-125, 42), (-125, 51), (-132, 55), (-140, 60),
        (-152, 58), (-164, 54), (-159, 60), (-166, 62),
    ),
    (
        (-122, 75), (-107, 80), (-93, 79), (-81, 84), (-64, 81), (-75, 76),
        (-85, 73), (-100, 75),
    ),
    (  # Greenland
        (-72, 77), (-57, 82), (-35, 83), (-18, 81), (-21, 73), (-32, 68),
        (-42, 60), (-51, 64), (-53, 70), (-62, 75),
    ),
    (  # South America
        (-81, 9), (-74, 12), (-65, 10), (-61, 9), (-52, 5), (-48, 0),
        (-41, -2), (-35, -6), (-38, -13), (-44, -23), (-50, -27), (-54, -34),
        (-59, -38), (-64, -47), (-68, -54), (-74, -50), (-74, -42),
        (-72, -32), (-71, -20), (-77, -12), (-81, -5),
    ),
    (  # Europe and Asia
        (-10, 36), (-9, 43), (-2, 44), (-5, 48), (4, 52), (9, 54),
        (13, 55), (7, 58), (6, 63), (15, 69), (29, 72), (31, 66), (44, 67),
        (45, 70), (58, 68), (68, 72), (79, 71), (89, 76), (105, 77),
        (118, 73), (139, 73), (154, 71), (166, 69), (179, 67), (179, 63),
        (166, 62), (162, 57), (158, 51), (154, 52), (156, 59), (148, 60),
        (142, 55), (137, 53), (142, 47), (133, 43), (129, 35), (126, 35),
        (125, 40), (121, 37), (122, 31), (119, 25), (114, 22), (108, 21),
        (109, 14), (104, 9), (103, 2), (100, 6), (98, 15), (94, 17),
        (91, 22), (87, 21), (81, 14), (77, 8), (72, 18), (68, 23), (60, 25),
        (56, 27), (51, 30), (56, 25), (58, 21), (50, 16), (44, 13),
        (42, 17), (36, 28), (32, 31), (36, 36), (28, 36), (26, 40),
        (22, 39), (19, 43), (13, 45), (17, 40), (15, 38), (10, 44), (6, 43),
        (1, 41), (-1, 37),
    ),
    (  # Africa
        (-17, 21), (-12, 29), (-6, 35), (3, 37), (11, 37), (11, 33),
        (20, 32), (26, 31), (34, 31), (36, 23), (43, 12), (51, 11),
        (48, 3), (42, -3), (40, -12), (35, -19), (33, -27), (27, -34),
        (18, -35), (14, -25), (12, -18), (13, -8), (9, 0), (10, 5),
        (3, 6), (-3, 5), (-8, 5), (-15, 11), (-17, 15),
    ),
    (  # Australia
        (112, -22), (115, -19), (122, -16), (128, -14), (132, -12), (137, -12),
        (137, -16), (142, -17), (143, -11), (148, -19), (153, -25),
        (151, -33), (146, -39), (140, -38), (135, -34), (130, -32),
        (122, -34), (115, -35),
    ),
    ((-24, 65), (-15, 67), (-13, 64), (-23, 63)),  # Iceland
    ((-8, 58), (-3, 59), (2, 52), (-5, 50), (-10, 52)),  # British Isles
    ((-85, 23), (-78, 23), (-73, 20), (-82, 20)),  # Cuba
    ((130, 32), (136, 35), (142, 44), (146, 44), (141, 37), (135, 33)),  # Japan
    ((95, 5), (100, 2), (106, -5), (103, -5), (99, -2)),  # Sumatra
    ((105, -6.8), (106, -5.9), (110, -6.5), (114.6, -7.8), (114.5, -8.8), (108, -7.8)),
    ((109, 0), (113, 6), (120, 6), (118, -4), (112, -4)),  # Borneo
    ((130, -2), (142, -3), (152, -6), (150, -10), (138, -7)),  # New Guinea
    ((49, -12), (50, -17), (47, -24), (43, -25), (44, -18)),  # Madagascar
    ((166, -47), (167, -43), (174, -38), (178, -36), (176, -42), (170, -46)),
)
MAP_ORIGIN = (51, 345)
MAP_SIZE = (922, 121)


@cache
def sans(size, bold=False):
    return ImageFont.truetype(SANS_BOLD if bold else SANS_REGULAR, size)


@cache
def serif(size):
    face = ImageFont.truetype(NOTO_SERIF, size)
    face.set_variation_by_name("Black")
    return face


def ink_width(face, text):
    left, _, right, _ = face.getbbox(text)
    return max(right, face.getlength(text)) - min(0, left)


def wrap_paragraph(text, face, width):
    lines = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}" if line else word
        if line and ink_width(face, candidate) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    lines.append(line)

    # Move a few words from the penultimate line to avoid an isolated last word.
    if len(lines) > 1:
        while ink_width(face, lines[-1]) < width * 0.38 and " " in lines[-2]:
            before, last_word = lines[-2].rsplit(" ", 1)
            lines[-2:] = [before, f"{last_word} {lines[-1]}"]
    return lines


def draw_lines(pen, x, y, width, lines, face, leading, fill):
    baseline = y - face.getbbox("H", anchor="ls")[1]
    bottom = y
    for line in lines:
        if ink_width(face, line) > width:
            raise ValueError(f"Line overflows {width}px: {line}")
        left, _, _, descent = face.getbbox(line, anchor="ls")
        pen.text((x - min(0, left), baseline), line, font=face, fill=fill, anchor="ls")
        bottom = max(bottom, baseline + descent)
        baseline += leading
    return bottom


def disk(pen, center, radius, fill):
    x, y = center
    pen.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)


def map_coordinates(longitude, latitude, width, height):
    # The rectangular projection runs from 90° N to 56° S.
    east = longitude + 180
    south = 90 - latitude
    return east * width / 360, south * height / 146


def coastline_samples(columns, rows):
    mask = Image.new("L", (columns, rows))
    pen = ImageDraw.Draw(mask)
    for outline in COASTLINES:
        projected = (
            map_coordinates(longitude, latitude, columns - 1, rows - 1)
            for longitude, latitude in outline
        )
        pen.polygon([(round(x), round(y)) for x, y in projected], fill=255)
    return mask.tobytes()


def draw_map_grid(pen, size, stroke):
    width, height = size
    for meridian in range(-150, 180, 30):
        x, _ = map_coordinates(meridian, 0, width, height)
        pen.line(((x, 0), (x, height - 1)), fill=MAP_GRID, width=stroke)
    for parallel in range(-30, 90, 30):
        _, y = map_coordinates(0, parallel, width, height)
        pen.line(((0, y), (width - 1, y)), fill=MAP_GRID, width=stroke)


def render_dotted_map():
    columns, rows = 185, 34
    oversampling = 3
    width, height = (side * oversampling for side in MAP_SIZE)
    canvas = Image.new("RGB", (width, height), MAP_BACKGROUND)
    pen = ImageDraw.Draw(canvas)
    draw_map_grid(pen, canvas.size, oversampling)

    # Space the samples across the full raster, including its edge pixels.
    sample_x = [round(col * (width - 1) / (columns - 1)) for col in range(columns)]
    sample_y = [round(row * (height - 1) / (rows - 1)) for row in range(rows)]
    for index, on_land in enumerate(coastline_samples(columns, rows)):
        if on_land:
            row, column = divmod(index, columns)
            disk(pen, (sample_x[column], sample_y[row]), 4, MAP_DOT)
    return canvas.resize(MAP_SIZE, Image.Resampling.LANCZOS)


def locate_map_pins():
    origin_x, origin_y = MAP_ORIGIN
    positions = []
    for number, (longitude, latitude), (offset_x, offset_y) in PINS:
        local_x, local_y = map_coordinates(longitude, latitude, *MAP_SIZE)
        x = origin_x + round(local_x)
        y = origin_y + round(local_y)
        positions.append((number, (x, y), (x + offset_x, y + offset_y)))
    return positions


def ticker_strip(width):
    glyphs = sans(40, True).getmask(TICKER, mode="L")
    coverage = Image.frombytes("L", glyphs.size, bytes(glyphs))
    return coverage.resize((width, 8), Image.Resampling.LANCZOS)


def mercury_artwork():
    scale = 3
    width, height = 72, 68
    illustration = Image.new("RGB", (width * scale, height * scale), INK)
    pen = ImageDraw.Draw(illustration)

    for x, y, radius in ((10, 14, 1), (58, 12, 1), (65, 43, 1), (18, 56, 1), (57, 55, 1)):
        disk(pen, (x * scale, y * scale), radius * scale, "#7085A4")

    orbit = Image.new("RGBA", illustration.size)
    orbit_pen = ImageDraw.Draw(orbit)
    orbit_pen.ellipse((3 * scale, 21 * scale, 68 * scale, 47 * scale), outline="#9A825A", width=scale)
    orbit = orbit.rotate(26, resample=Image.Resampling.BICUBIC)
    illustration.paste(orbit, mask=orbit.getchannel("A"))

    disk(pen, (36 * scale, 34 * scale), 20 * scale, "#8E755A")
    disk(pen, (34 * scale, 32 * scale), 17 * scale, "#D8BC8C")
    for x, y, radius in ((27, 24, 4), (38, 29, 3), (27, 37, 2), (43, 38, 5), (34, 44, 2), (40, 20, 2)):
        disk(pen, (x * scale, y * scale), radius * scale, "#AD8D67")
        disk(pen, ((x - 1) * scale, (y - 1) * scale), (radius - 0.9) * scale, "#BA9D76")
    disk(pen, (62 * scale, 23 * scale), 2.5 * scale, GOLD)
    return illustration.resize((width, height), Image.Resampling.LANCZOS)


class FrontPage:
    def __init__(self):
        self.image = Image.new("RGB", (PAGE, PAGE), PAPER)
        self.pen = ImageDraw.Draw(self.image)

    def rule(self, y, color=INK, width=1):
        self.pen.line((MARGIN, y, RIGHT, y), fill=color, width=width)

    def badge(self, center, number, radius, *, space=False):
        disk(self.pen, center, radius, GOLD if space else RED)
        self.pen.text(center, str(number), font=sans(radius + 6, True),
                      fill=INK if space else PAPER, anchor="mm")

    def masthead(self):
        font = sans(19, True)
        tracking = 4
        advances = [font.getlength(char) + tracking for char in MASTHEAD]
        x = (PAGE - sum(advances) + tracking) / 2
        self.pen.line((MARGIN, 21, x - 18, 21), fill=HAIRLINE)
        self.pen.line((PAGE - x + 18, 21, RIGHT, 21), fill=HAIRLINE)
        for char, advance in zip(MASTHEAD, advances, strict=True):
            self.pen.text((x, 28), char, font=font, fill=INK, anchor="ls")
            x += advance

        face = serif(59)
        gap = 20
        width = face.getlength(WEEKDAY) + gap + face.getlength(DATE)
        start = (PAGE - width) / 2
        date_x = start + face.getlength(WEEKDAY) + gap
        left = start + face.getbbox(WEEKDAY, anchor="ls")[0]
        right = date_x + face.getbbox(DATE, anchor="ls")[2]
        if not DATE_MARGIN <= left < right <= PAGE - DATE_MARGIN:
            raise ValueError("The masthead date must stay within the 34px side margins")
        self.pen.text((start, 85), WEEKDAY, font=face, fill=RED, anchor="ls")
        self.pen.text((date_x, 85), DATE, font=face, fill=INK, anchor="ls")
        self.rule(104, width=2)

    def story(self, number, left, top, right, bottom, headline_size, *, background=None, space=False):
        story = STORIES[number - 1]
        if background:
            self.pen.rectangle((left, top, right, bottom), fill=background)
        if space:
            self.image.paste(mercury_artwork(), (right - 81, top + 5))

        x = left + 11
        width = right - 11 - x
        badge_y = top + 17
        copy_color = PAPER if space else INK
        label_color = GOLD if space else RED
        self.badge((x + 11, badge_y), number, 11, space=space)
        self.pen.text((x + 31, badge_y), story.location, font=sans(15, True),
                      fill=label_color, anchor="lm")

        head_width = width - 70 if space else width
        headline_bottom = draw_lines(self.pen, x, top + 32, head_width, story.headline,
                                     serif(headline_size), headline_size, copy_color)
        face = sans(15)
        body = wrap_paragraph(story.body, face, width)
        body_bottom = draw_lines(self.pen, x, headline_bottom + 5, width, body, face, 16, copy_color)

        if number == 1:
            body_bottom = draw_lines(self.pen, x, body_bottom + 6, width, (CLAIM_NOTE,),
                                     sans(12, True), 14, RED)
        if body_bottom > bottom - 4:
            raise ValueError(f"Story {number} extends past its panel ({body_bottom} > {bottom - 4})")

    def map_band(self):
        top, bottom = 322, 471
        self.pen.rectangle((MARGIN, top, RIGHT, bottom), fill=MAP_BACKGROUND)
        self.rule(top)
        self.pen.text((MARGIN + 11, top + 8), "WHERE IT HAPPENED", font=sans(13, True),
                      fill=INK, anchor="lt")
        self.image.paste(render_dotted_map(), MAP_ORIGIN)
        self.rule(bottom, HAIRLINE)
        self.draw_map_pins()

    def draw_map_pins(self):
        pins = locate_map_pins()
        badge_centers = [center for _, _, center in pins]
        if any(dist(first, second) < 30 for first, second in combinations(badge_centers, 2)):
            raise ValueError("Map badges need at least 30px center-to-center clearance")
        if any(dist(anchor, center) < 18 for _, anchor, _ in pins for center in badge_centers):
            raise ValueError("A map badge covers a geographic anchor")

        # Lay down every leader before marking the two ends.
        for _, anchor, badge in pins:
            for color, width in ((MAP_BACKGROUND, 4), (RED, 2)):
                self.pen.line((anchor, badge), fill=color, width=width)
        for number, anchor, badge in pins:
            for center, radius, color in ((anchor, 4, PAPER), (anchor, 2.5, RED), (badge, 14, PAPER)):
                disk(self.pen, center, radius, color)
            self.badge(badge, number, 12)

    def data_bar(self):
        bar_top, bar_bottom = 924, 970
        label_y, value_y = bar_top + 8, bar_top + 21
        label_font, value_font = sans(11, True), serif(23)
        self.pen.rectangle(((MARGIN, bar_top), (RIGHT, bar_bottom)), fill=SAND)
        self.rule(bar_top, width=2)

        boundaries = (MARGIN, 250, 430, 644, 826, RIGHT)
        for (start, end), figure in zip(pairwise(boundaries), FIGURES, strict=True):
            title, value = figure.split(": ", maxsplit=1)
            label = f"{title}:"
            if ink_width(label_font, label) > (end - start) - 12:
                raise ValueError(f"Data label overflows: {label}")
            if start > MARGIN:
                self.pen.line(((start, label_y), (start, bar_bottom - 6)), fill=HAIRLINE)
            midpoint = (start + end) / 2
            self.pen.text((midpoint, label_y), label, font=label_font, fill=INK, anchor="mt")
            self.pen.text((midpoint, value_y), value, font=value_font, fill=RED, anchor="mt")

    def ticker(self):
        panel_top = 976
        left, right = MARGIN + 9, RIGHT - 9
        self.pen.rectangle(((MARGIN, panel_top), (RIGHT, panel_top + 32)), fill=INK)
        self.pen.text((left, panel_top + 5), "ALSO TODAY",
                      font=sans(10, True), anchor="lt", fill=GOLD)
        rule_y = panel_top + 9
        self.pen.line(((left + 73, rule_y), (right, rule_y)), fill="#80745E")
        self.image.paste(PAPER, (left, panel_top + 19), ticker_strip(right - left))


def front_page():
    page = FrontPage()
    page.masthead()
    page.story(1, MARGIN, 110, 501, 318, 31, background=SAND)
    page.story(2, 523, 110, RIGHT, 318, 31, background="#F2EBDE")
    page.map_band()

    for first, top, bottom in ((3, 474, 621), (5, 621, 769), (7, 769, 919)):
        page.rule(top, HAIRLINE)
        page.pen.line((512, top + 8, 512, bottom - 7), fill=HAIRLINE)
        page.story(first, MARGIN, top, 501, bottom, 24)
        if first == 7:
            page.story(8, 523, top + 4, RIGHT, bottom, 22, background=INK, space=True)
        else:
            page.story(first + 1, 523, top, RIGHT, bottom, 22 if first == 3 else 24)

    page.data_bar()
    page.ticker()
    return page.image


def png_bytes():
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Title", f"{MASTHEAD} — {WEEKDAY} {DATE}")
    # Keep the full text available to readers alongside the raster typography.
    description = [f"{MASTHEAD} — {WEEKDAY} {DATE}"]
    for number, story in enumerate(STORIES, 1):
        description.append(f"{number}. {' '.join(story.headline)} — {story.location}.\n{story.body}")
        if number == 1:
            description.append(CLAIM_NOTE)
    description.extend(FIGURES)
    description.append(f"ALSO TODAY\n{TICKER}")
    metadata.add_itxt("Description", "\n\n".join(description), lang="en", zip=True)

    output = BytesIO()
    front_page().save(output, format="PNG", pnginfo=metadata, optimize=True)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    destinations = parser.add_mutually_exclusive_group()
    destinations.add_argument("output", nargs="?", type=Path)
    destinations.add_argument("--stdout", action="store_true")
    args = parser.parse_args()
    if not all(font.is_file() for font in (NOTO_SERIF, SANS_REGULAR, SANS_BOLD)):
        raise SystemExit(69)
    image = png_bytes()
    if args.stdout:
        sys.stdout.buffer.write(image)
    else:
        output = args.output or Path(__file__).resolve().with_name("entry.png")
        output.write_bytes(image)


if __name__ == "__main__":
    main()
