from cianparser.parser import ParserOffers
def parse(rooms):
    parser = ParserOffers(
        rooms=rooms,
    )
    parser.run()
    return parser.result


