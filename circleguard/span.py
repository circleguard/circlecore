class Span(set):
    """
    A set of numbers represented by a string, which can include ranges or
    single numbers, separated by a comma.

    Notes
    -----
    Spans can only range from 1 to 100 inclusive.

    Examples
    --------
    >>> Span("1-3,6,2-4")
    {1, 2, 3, 4, 6}
    """

    def __init__(self, data):
        # allow passing as either span or string
        if not isinstance(data, (Span, str)):
            raise ValueError(f"Expected data to be a str or Span, got type "
                f"{type(data)}.")
        if isinstance(data, Span):
            # python allows initializing a set with a set
            super().__init__(data)
        elif isinstance(data, str):
            span_set = self._to_set(data)
            super().__init__(span_set)

        if max(self) > 100:
            raise ValueError("Spans can only range from 1 to 100 inclusive. "
                f"The largest element passed was {max(self)}")

    def _to_set(self, span):
        """
        Converts a span to the set of numbers covered by that span.

        Parameters
        ----------
        span: str
            The span of numbers to convert to a set. A number may occur more
            than once - whether explicitly or in a range - in the span, but
            will only occur once in the returned set.

        Returns
        -------
        set
            The set of numbers described by the ``span``.

        Examples
        --------
        >>> _to_set("1-3,6,2-4")
        {1, 2, 3, 4, 6}
        """
        ret = set()
        for s in span.split(","):
            if "-" in s:
                p = s.split("-")
                l = list(range(int(p[0]), int(p[1]) + 1))
                ret.update(l)
            else:
                ret.add(int(s))
        return ret
