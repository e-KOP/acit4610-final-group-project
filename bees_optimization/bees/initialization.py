import random


def random_tour(n, rng):
    if n < 2:
        raise ValueError("TSP requires at least 2 cities")

    # City 1 must remain fixed
    cities = list(range(2, n + 1))

    # Randomize the remaining cities
    rng.shuffle(cities)

    return [1] + cities


def initialize_scouts(n, population_size, rng):
    if population_size < 1:
        raise ValueError("Population size must be positive")

    return [
        random_tour(n, rng)
        for _ in range(population_size)
    ]



if __name__ == "__main__":
    from .tsplib import validate_tour

    rng = random.Random(42)

    for i in range(5):
        tour = random_tour(6, rng)

        validate_tour(tour, 6)

        print(f"Scout {i + 1}: {tour}")

    print("All initialization tests passed!")


    rng1 = random.Random(42)
    rng2 = random.Random(42)

    tour1 = random_tour(51, rng1)
    tour2 = random_tour(51, rng2)

    assert tour1 == tour2

    print("Reproducibility test passed!")


    from .tsplib import (
        load_tsplib,
        validate_tsplib,
        create_distance_matrix,
        calculate_tour_length
    )

    metadata, coordinates = load_tsplib(
        "bees_optimization/data/tsplib/eil51.tsp"
    )

    validate_tsplib(metadata, coordinates)

    matrix = create_distance_matrix(coordinates)

    scouts = initialize_scouts(
        n=51,
        population_size=10,
        rng=random.Random(42)
    )

    lengths = [
        calculate_tour_length(tour, matrix)
        for tour in scouts
    ]

    print("\nInitial scout lengths:", lengths)
    print("Best initial length:", min(lengths))

    assert len(scouts) == 10
    assert len(lengths) == 10
    assert all(validate_tour(tour, 51) for tour in scouts)

    print("Initial population tests passed!")


