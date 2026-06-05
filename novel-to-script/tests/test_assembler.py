"""Integration test for assembler edge cases."""
from src.schema.screenplay import CharacterRole
from src.pipeline.assembler import _build_characters, _build_acts, _parse_location_type

# Test location type parsing
assert _parse_location_type("INT") is not None
assert _parse_location_type("EXT") is not None
assert _parse_location_type("random") is not None

# Test character building with role_description that doesn't match enum
chars = _build_characters([
    {"id": "a", "name": "Alice", "role_description": "protagonist"},
    {"id": "b", "name": "Bob", "role_description": "boss"},
    {"id": "c", "name": "Charlie", "role_description": "xx_nonexistent_xx"},
])
assert len(chars) == 3
print(f"Chars: {[(c.name, c.role.value) for c in chars]}")

# Test acts building with edge cases
chapters_data = [
    {
        "chapter_title": "Ch1",
        "scenes": [
            {"location_type": "INT", "location": "Room", "time": "Day", "summary": "Opening",
             "characters_in_scene": ["a"], "beats": [
                 {"type": "action", "description": "Hello."},
                 {"type": "dialogue", "character": "a", "line": "Hi."},
                 {"type": "dialogue", "character": "z", "line": "unknown char"},
                 {"type": "transition", "transition": "CUT TO:"},
                 {"type": "unknown_type", "description": "Should be skipped"},
             ]}
        ]
    },
    {
        "chapter_title": "Ch2",
        "scenes": []  # empty scenes
    },
]
acts = _build_acts(chapters_data, {"a", "b"})
assert len(acts) == 1  # 2 chapters -> single act
assert len(acts[0].scenes) == 1  # only first chapter has scenes
assert len(acts[0].scenes[0].beats) == 4  # action, dialogue(a), dialogue(unknown), transition

print(f"Acts: {len(acts)}")
for act in acts:
    for sc in act.scenes:
        print(f"  Scene {sc.scene_number}: {len(sc.beats)} beats")
        for b in sc.beats:
            print(f"    {b.type}")

print("\nAll assembler tests passed!")
