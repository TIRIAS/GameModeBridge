"""exe 아이콘(.ico)과 안드로이드 적응형 아이콘 전경 PNG를 gmb.icon으로 생성함.

실행: pc 폴더에서 .venv\\Scripts\\python.exe tools\\make_icons.py
결과물은 저장소에 커밋함 (비밀 정보 아님). 아이콘 모양을 바꾸면 다시 실행함.
"""

import sys
from pathlib import Path

from PIL import Image

PC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PC))

from gmb.icon import app_icon, glyph  # noqa: E402

RES = PC.parent / "android" / "app" / "src" / "main" / "res"
# 적응형 아이콘 캔버스 108dp 중 안전 영역 66dp 안에 그림이 들어가도록 줄임
_FOREGROUND_RATIO = 0.667
_DENSITIES = {"mdpi": 1.0, "hdpi": 1.5, "xhdpi": 2.0, "xxhdpi": 3.0, "xxxhdpi": 4.0}


def make_ico(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    app_icon(256).save(path, sizes=[(s, s) for s in sizes])


def make_foreground(size: int) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    g = glyph(round(size * _FOREGROUND_RATIO))
    off = (size - g.width) // 2
    canvas.alpha_composite(g, (off, off))
    return canvas


def main() -> None:
    make_ico(PC / "assets" / "GameModeBridge.ico")
    for name, scale in _DENSITIES.items():
        out = RES / f"mipmap-{name}" / "ic_launcher_foreground.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        make_foreground(round(108 * scale)).save(out, optimize=True)
    print("아이콘 생성 완료")


if __name__ == "__main__":
    main()
