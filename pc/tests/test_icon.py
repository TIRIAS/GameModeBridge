from gmb.icon import BRAND, app_icon, glyph


def test_app_icon_size_and_corners():
    img = app_icon(64, (46, 160, 67))
    assert img.size == (64, 64)
    assert img.getpixel((0, 0))[3] == 0  # 둥근 모서리는 투명
    assert img.getpixel((32, 4))[:3] == (46, 160, 67)  # 위쪽 가장자리는 배경색


def test_glyph_has_transparent_background_and_white_shape():
    img = glyph(108)
    assert img.getpixel((2, 2))[3] == 0
    assert img.getchannel("A").getextrema() == (0, 255)


def test_brand_color_matches_android_background():
    from pathlib import Path

    xml = (Path(__file__).resolve().parents[2] / "android/app/src/main/res/values/ic_launcher_background.xml").read_text(encoding="utf-8")
    assert "#%02X%02X%02X" % BRAND in xml
