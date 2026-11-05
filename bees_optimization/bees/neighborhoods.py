import random


def swap_neighbor(tour, rng):
    neighbor = tour.copy()

    # Choose two different positions, excluding city 1
    i, j = rng.sample(range(1, len(tour)), 2)

    # Swap the cities
    neighbor[i], neighbor[j] = neighbor[j], neighbor[i]

    return neighbor

def reverse_neighbor(tour, rng):
    neighbor = tour.copy()

    # Choose two positions, excluding city 1
    i, j = sorted(
        rng.sample(range(1, len(tour)), 2)
    )

    # Reverse the selected segment, including both endpoints
    neighbor[i:j + 1] = reversed(neighbor[i:j + 1])

    return neighbor


if __name__ == "__main__":
    from .tsplib import validate_tour

    rng = random.Random(42)

    original = [1, 2, 3, 4, 5, 6]

    swapped = swap_neighbor(original, rng)
    reversed_route = reverse_neighbor(original, rng)

    print("Original:", original)
    print("Swap:", swapped)
    print("Reversal:", reversed_route)

    # Both generated routes must be valid
    assert validate_tour(swapped, 6)
    assert validate_tour(reversed_route, 6)

    # Original must remain unchanged
    assert original == [1, 2, 3, 4, 5, 6]

    # Exactly two positions must change after a swap
    changed_positions = sum(
        a != b for a, b in zip(original, swapped)
    )

    assert changed_positions == 2

    print("All neighborhood tests passed!")


    from .tsplib import (
        load_tsplib,
        validate_tsplib,
        create_distance_matrix,
        calculate_tour_length,
    )

    metadata, coordinates = load_tsplib(
        "bees_optimization/data/tsplib/eil51.tsp"
    )

    validate_tsplib(metadata, coordinates)

    matrix = create_distance_matrix(coordinates)

    original = list(range(1, 52))

    swapped = swap_neighbor(original, rng)
    reversed_route = reverse_neighbor(original, rng)

    print("\nActual eil51 results:")
    print("Original length:", calculate_tour_length(original, matrix))
    print("Swap length:", calculate_tour_length(swapped, matrix))
    print("Reversal length:", calculate_tour_length(reversed_route, matrix))

