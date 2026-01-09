# rubik_sim/logic/scramble.py
import random

FACES = ["U", "D", "L", "R", "F", "B"]
SUFFIX = ["", "'", "2"]

def generate_scramble(n: int, seed: int | None = None) -> str:
    rng = random.Random(seed)
    seq = []
    last_face = None
    for _ in range(n):
        face = rng.choice([m for m in FACES if m != last_face])
        last_face = face
        seq.append(face + rng.choice(SUFFIX))
    return " ".join(seq)
