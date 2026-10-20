"""앱 아이콘 그리기 (게임 패드 + 신호 표시). 트레이 아이콘과 exe, 안드로이드 아이콘 생성에 함께 씀.

좌표는 0~1 비율로 정의하고, 크게 그린 뒤 줄여서 작은 크기에서도 가장자리가 매끄럽게 함.
"""

from PIL import Image, ImageDraw

BRAND = (38, 56, 89)  # 남색 배경
_SCALE = 4


def _glyph_mask(size: int) -> Image.Image:
    """흰색 부분이 255인 글리프 마스크 (게임 패드 몸체와 신호 호)."""
    big = size * _SCALE
    mask = Image.new("L", (big, big), 0)
    d = ImageDraw.Draw(mask)

    def box(x0, y0, x1, y1):
        return (x0 * big, y0 * big, x1 * big, y1 * big)

    # 신호 호 2개 (PC에서 휴대폰으로 보내는 신호)
    w = max(1, round(0.055 * big))
    for r in (0.11, 0.21):
        d.arc(box(0.5 - r, 0.40 - r, 0.5 + r, 0.40 + r), 225, 315, fill=255, width=w)
    d.ellipse(box(0.465, 0.365, 0.535, 0.435), fill=255)

    # 게임 패드 몸체와 손잡이
    d.rounded_rectangle(box(0.12, 0.47, 0.88, 0.76), radius=0.14 * big, fill=255)
    d.ellipse(box(0.12, 0.56, 0.40, 0.88), fill=255)
    d.ellipse(box(0.60, 0.56, 0.88, 0.88), fill=255)

    # 십자 버튼과 버튼 2개는 뚫음
    d.rectangle(box(0.235, 0.585, 0.385, 0.635), fill=0)
    d.rectangle(box(0.285, 0.535, 0.335, 0.685), fill=0)
    d.ellipse(box(0.615, 0.535, 0.685, 0.605), fill=0)
    d.ellipse(box(0.685, 0.615, 0.755, 0.685), fill=0)
    return mask.resize((size, size), Image.LANCZOS)


def glyph(size: int, color=(255, 255, 255)) -> Image.Image:
    """투명 배경 위 글리프 (안드로이드 적응형 아이콘 전경, 단색 아이콘용)."""
    img = Image.new("RGBA", (size, size), color + (0,))
    img.putalpha(_glyph_mask(size))
    return img


def app_icon(size: int, bg=BRAND) -> Image.Image:
    """둥근 사각형 배경 위 흰색 글리프 (exe 아이콘, 트레이 아이콘)."""
    big = size * _SCALE
    plate = Image.new("L", (big, big), 0)
    ImageDraw.Draw(plate).rounded_rectangle((0, 0, big - 1, big - 1), radius=0.22 * big, fill=255)
    img = Image.new("RGBA", (size, size), bg + (255,))
    img.putalpha(plate.resize((size, size), Image.LANCZOS))
    white = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    img.paste(white, (0, 0), _glyph_mask(size))
    return img
