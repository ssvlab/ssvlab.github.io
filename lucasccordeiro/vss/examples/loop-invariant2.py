def main() -> None:
    x: int = 0
    y: int = 50
    x = x + 1
    if x > 50:
        y = y + 1
    assert y == 100

main()

