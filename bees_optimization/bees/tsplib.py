# AI-assisted parser validation additions; see docs/ai_usage.md.
from pathlib import Path
import math


def load_tsplib(file_path):
    file_path = Path(file_path)

    metadata = {}
    coordinates = {}
    reading_coordinates = False

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            if line == "NODE_COORD_SECTION":
                if reading_coordinates:
                    raise ValueError("Duplicate NODE_COORD_SECTION")
                reading_coordinates = True
                continue

            if line == "EOF":
                break

            if reading_coordinates:
                parts = line.split()

                if len(parts) != 3:
                    raise ValueError("Expected city ID and two coordinates")

                city_id = int(parts[0])
                x = float(parts[1])
                y = float(parts[2])

                if not math.isfinite(x) or not math.isfinite(y):
                    raise ValueError("City coordinates must be finite")

                if city_id in coordinates:
                    raise ValueError(
                        f"Duplicate city ID: {city_id}"
                    )

                coordinates[city_id] = (x, y)

            elif ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

    if not reading_coordinates:
        raise ValueError("Missing NODE_COORD_SECTION")
    return metadata, coordinates


def validate_tsplib(metadata, coordinates):
    required_fields = [
        "NAME",
        "TYPE",
        "DIMENSION",
        "EDGE_WEIGHT_TYPE"
    ]

    # Check that required metadata exists
    for field in required_fields:
        if field not in metadata:
            raise ValueError(f"Missing field: {field}")

    # Check problem type
    if metadata["TYPE"] != "TSP":
        raise ValueError("Only TSP instances are supported")

    # Check distance calculation type
    if metadata["EDGE_WEIGHT_TYPE"] != "EUC_2D":
        raise ValueError("Only EUC_2D distances are supported")

    # Check number of cities
    dimension = int(metadata["DIMENSION"])

    if dimension < 2:
        raise ValueError("TSP requires at least 2 cities")

    if len(coordinates) != dimension:
        raise ValueError(
            f"Expected {dimension} cities, "
            f"found {len(coordinates)}"
        )

    # Check that city IDs are consecutive, starting at 1
    expected_ids = set(range(1, dimension + 1))
    actual_ids = set(coordinates.keys())

    if actual_ids != expected_ids:
        raise ValueError("Invalid city identifiers")

    return True


def calculate_distance(city1, city2):
    x1, y1 = city1
    x2, y2 = city2

    distance = math.sqrt(
        (x1 - x2) ** 2 + (y1 - y2) ** 2
    )

    return math.floor(distance + 0.5)


def create_distance_matrix(coordinates):
    n = len(coordinates)

    matrix = [[0] * n for _ in range(n)]

    for i in range(n):
        for j in range(i + 1, n):
            distance = calculate_distance(
                coordinates[i + 1],
                coordinates[j + 1]
            )

            matrix[i][j] = distance
            matrix[j][i] = distance

    return matrix


def validate_tour(tour, n):
    if len(tour) != n:
        raise ValueError("Tour has incorrect length")

    if tour[0] != 1:
        raise ValueError("Tour must start at city 1")

    expected_cities = set(range(1, n + 1))

    if set(tour) != expected_cities:
        raise ValueError("Tour contains missing or invalid cities")

    return True


def calculate_tour_length(tour, distance_matrix):
    n = len(distance_matrix)

    validate_tour(tour, n)

    total_distance = 0

    # Calculate distances between consecutive cities
    for i in range(n - 1):
        current_city = tour[i] - 1
        next_city = tour[i + 1] - 1

        total_distance += distance_matrix[current_city][next_city]

    # Add distance from final city back to city 1
    last_city = tour[-1] - 1
    starting_city = tour[0] - 1

    total_distance += distance_matrix[last_city][starting_city]

    return total_distance



if __name__ == "__main__":
    metadata, coordinates = load_tsplib(
        "bees_optimization/data/tsplib/eil51.tsp"
    )

    validate_tsplib(metadata, coordinates)

    distance = calculate_distance(
        coordinates[1],
        coordinates[2]
    )

    print("City 1:", coordinates[1])
    print("City 2:", coordinates[2])
    print("Distance:", distance)

    assert distance == 12
    assert calculate_distance(
        coordinates[1], coordinates[1]
    ) == 0
    assert calculate_distance((0, 0), (3, 4)) == 5
    assert calculate_distance((0, 0), (2.5, 0)) == 3

    print("All distance tests passed!")


    matrix = create_distance_matrix(coordinates)

    print("Matrix dimensions:", len(matrix), "x", len(matrix[0]))
    print("Distance from city 1 to city 2:", matrix[0][1])

    assert len(matrix) == 51
    assert all(len(row) == 51 for row in matrix)

    for i in range(51):
        assert matrix[i][i] == 0

        for j in range(51):
            assert matrix[i][j] == matrix[j][i]

    print("All matrix tests passed!")


    # Small artificial TSP example
    test_matrix = [
        [0, 10, 15, 20],
        [10, 0, 35, 25],
        [15, 35, 0, 30],
        [20, 25, 30, 0]
    ]

    test_tour = [1, 2, 4, 3]

    length = calculate_tour_length(
        test_tour,
        test_matrix
    )

    print("Test tour:", test_tour)
    print("Test tour length:", length)

    assert length == 80

    print("Tour calculation test passed!")


    # Create a simple route visiting cities in ID order
    tour = list(range(1, 52))

    validate_tour(tour, 51)

    tour_length = calculate_tour_length(
        tour,
        matrix
    )

    print("eil51 sequential tour length:", tour_length)


    # Test invalid routes
    invalid_tours = [
        [1, 2, 3],        # Too few cities
        [2, 1, 3, 4],     # Wrong starting city
        [1, 2, 2, 4],     # Duplicate city
        [1, 2, 3, 5],     # Invalid city ID
        [1, 2, 3, 4, 1]   # City 1 repeated
    ]

    for invalid_tour in invalid_tours:
        try:
            validate_tour(invalid_tour, 4)
        except ValueError:
            print(f"Correctly rejected: {invalid_tour}")
        else:
            raise AssertionError(
                f"Invalid tour accepted: {invalid_tour}"
            )

    print("All invalid tour tests passed!")



    original = [1, 2, 4, 3]
    reversed_tour = [1, 3, 4, 2]

    assert calculate_tour_length(
        original, test_matrix
    ) == calculate_tour_length(
        reversed_tour, test_matrix
    )

    print("Route reversal test passed!")



