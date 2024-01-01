from vast_ai import VastAPIHelper


if __name__ == '__main__':
    api = VastAPIHelper("5efb81d9bbc736c393b7feef35197d3646b6842c5ad4dbb3ffee83e7e4601796")
    api.list_available_instances()