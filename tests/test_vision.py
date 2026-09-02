"""Tests for multimodal vision helpers."""

from __future__ import annotations

from pathlib import Path

from friday.llm.vision import (
    build_user_content,
    image_to_data_url,
    looks_like_vision_model,
    pick_vision_model,
)


def test_looks_like_vision_model():
    assert looks_like_vision_model("qwen2-vl-7b-instruct")
    assert looks_like_vision_model("llava-v1.6-mistral-7b")
    assert not looks_like_vision_model("microsoft/phi-4")


def test_pick_vision_model_prefers_explicit():
    assert (
        pick_vision_model(["phi-4", "llava"], preferred="my-vlm") == "my-vlm"
    )


def test_pick_vision_model_auto():
    assert pick_vision_model(["microsoft/phi-4", "qwen2-vl-7b"]) == "qwen2-vl-7b"


def test_build_user_content_text_only():
    assert build_user_content("ola", None) == "ola"
    assert build_user_content("ola", []) == "ola"


def test_build_user_content_with_image(tmp_path: Path):
    img = tmp_path / "x.png"
    # Minimal 1x1 PNG
    img.write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
        )
    )
    content = build_user_content(
        "o que e isto?",
        [{"path": str(img), "filename": "x.png", "kind": "image", "mime": "image/png"}],
    )
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    url = content[1]["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")


def test_image_to_data_url(tmp_path: Path):
    p = tmp_path / "a.jpg"
    p.write_bytes(b"\xff\xd8\xff\xd9")
    url = image_to_data_url(p, mime="image/jpeg")
    assert url.startswith("data:image/jpeg;base64,")
