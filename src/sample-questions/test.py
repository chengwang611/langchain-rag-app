from typing import Callable


# Different functions
def process_name(value):
    print(f"Processing name: {value}")


def process_age(value):
    print(f"Processing age: {value}")


def process_city(value):
    print(f"Processing city: {value}")


def process_default(key, value):
    print(f"Unknown field {key}: {value}")


def main():
    # Step 1: Create an empty dictionary
    person = {}

    # Step 2: Add key-value pairs
    person["name"] = "Alice"
    person["age"] = 30
    person["city"] = "Toronto"

    print("Dictionary:")
    print(person)

    # Step 3: Map keys to functions
    handlers: dict[str, Callable] = {
        "name": process_name,
        "age": process_age,
        "city": process_city,
    }

    # Step 4: Loop through the dictionary
    for key, value in person.items():

        if key in handlers:
            handlers[key](value)
        else:
            process_default(key, value)


if __name__ == "__main__":
    main()