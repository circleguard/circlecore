class Span():
    def __init__(self, span):
        self.span = span

    def to_set(self):
        """
        Converts a span to the set of numbers covered by that span.

        Parameters
        ----------
        span: str
            The span of numbers to convert to a set. A number may occur more than
            once - whether explicitly or in a range - in the span, but will
            only occur once in the returned set.

        Returns
        -------
        set
            The set of numbers described by the `span`.

        Examples
        --------
        >>> span_to_list("1-3,6,2-4")
        {1, 2, 3, 4, 6}
        """
        ret = set()
        for s in self.span.split(","):
            if "-" in s:
                p = s.split("-")
                l = list(range(int(p[0]), int(p[1])+1))
                ret.update(l)
            else:
                ret.add(int(s))
        return ret

    def max(self):
        # could probably optimize out the ``to_set``` call, but it's cheap
        # anyway
        return max(self.to_set())

    @classmethod
    def from_string_or_span(cls, data):
        if isinstance(data, Span):
            return data
        if isinstance(data, str):
            return Span(data)
        raise ValueError(f"Expected data to be a str or Span, got type {type(data)}.")

    def __eq__(self, span):
        if not isinstance(span, Span):
            return False
        return self.to_set() == span.to_set()
