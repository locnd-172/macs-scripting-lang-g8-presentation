class SuppressValueError:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:  # no exception was raised
            return False

        # True suppresses ValueError
        # False propagates other exceptions.
        return issubclass(exc_type, ValueError)


def show_suppressed_value_error():
    with SuppressValueError():
        int("not a number")
    print("Continued after ValueError was suppressed.")


def show_propagated_type_error():
    try:
        with SuppressValueError():
            raise TypeError("wrong type")
    except TypeError as error:
        print(f"TypeError reached the caller: {error}")


def main():
    show_suppressed_value_error()
    show_propagated_type_error()


if __name__ == "__main__":
    main()
