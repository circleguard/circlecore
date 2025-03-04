# Style

We follow [numpy style](https://numpydoc.readthedocs.io/en/latest/format.html#docstring-standard) docstrings, with the following exceptions.

## Backticks

We use [sphinx](http://www.sphinx-doc.org/en/master/) to build our documentation, and as such use double backticks to represent inline literals such as variables, whereas numpy suggests a single backtick.

### Numpy

```python
def add(a, b):
    """
    Adds `a` and `b`.

    Parameters
    ----------
    a: int
        The first number to add.
    b: int
        The second number to add.

    Returns
    -------
    int
        The sum of `a` and `b`.
    """
    return a + b
```

### Circlecore

```python
def add(a, b):
    """
    Adds ``a`` and ``b``.

    Parameters
    ----------
    a: int
        The first number to add.
    b: int
        The second number to add.

    Returns
    -------
    int
        The sum of ``a`` and ``b``.
    """
    return a + b
```

## Colons

Numpy has colons in the middle of the argument name and its type. For no reason other than aesthetics, we place the colon to the side of the name.

### Numpy

```python
def add(a, b):
    """
    Adds ``a`` and ``b``.

    Parameters
    ----------
    a : int
        The first number to add.
    b : int
        The second number to add.

    Returns
    -------
    int
        The sum of ``a`` and ``b``.
    """
    return a + b
```

### Circlecore

```python
def add(a, b):
    """
    Adds ``a`` and ``b``.

    Parameters
    ----------
    a: int
        The first number to add.
    b: int
        The second number to add.

    Returns
    -------
    int
        The sum of ``a`` and ``b``.
    """
    return a + b
```
