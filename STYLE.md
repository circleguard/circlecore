# Style

This document lays out the agreed upon style for code and commits to this repository.

## Files

### Docstrings

In general, we adhere to [google's style](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings) for docstrings, but the following style rules should be followed above all others.

* Use 3 double (not single) quotes for a docstring
* Unless the docstring is only one line, begin the docstring with a newline (documentation should not go on the same line as the triple quotes)
* One line of space should be left after the closing triple quotes
* The description of a function should be in the present tense (`Returns the name of the user`) rather than the imperative mood (`Return the name of the user`)
* Every sentence in a docstring should end with a period (even the description of `Args:`, `Returns:`, etc)
* Arg types should be Capitalized, even primitives. Primitive args should use the full length name (`Boolean` instead of `bool`, `Integer` instead of `int`, etc). If an arg can be multiple types, denote that with `[Type1 or Type2] arg1: description`, with the brackets included.

A docstring is structured as follows:

```python
def method(arg1, arg2):
    """
    [Description]

    [Longer Description]

    Args:
        [arg type] [arg name]: [description of arg]
        [arg type] [arg name]: [description of arg]

    Returns:
        [Description of return value]

    Raises:
        [error name]: [description of when this error is raised]
    """
```

Here is an example docstring that adheres to all guidelines:
```python
def from_path(path, useless_var):
    """
    Creates a Replay instance from the data contained by file at the given path.

    Args:
        [String or Path] path: The absolute path to the replay file.
        Integer useless_var: Just here for demonstration.

    Returns:
        The Replay instance created from the given path.
    """
```

Classes documentation is a little different. Classes follow all the same guidelines except they take no `Args`, have no `Return` value, but have an `Attributes` section that lists the variables you can expect to access at any time from an instance of this class. These attributes are often identical to the documentation on the classe's \__init__ method, but can include attributes that are not passed to \__init__ but still defined at instantiation time.

```python
class Comparer:
    """
    A class for managing a set of replay comparisons.

    Attributes:
        List replays1: A list of Replay instances to compare against replays2.
        List replays2: A list of Replay instances to be compared against.
        Integer threshold: If a comparison scores below this value, the result is printed.
    """

    def __init__(self, threshold, replays1, replays2=None):
        """
        Initializes a Comparer instance.

        Note that the order of the two replay lists has no effect; they are only numbered for consistency.
        Comparing 1 to 2 is the same as comparing 2 to 1.

        Args:
            List replays1: A list of Replay instances to compare against replays2.
            List replays2: A list of Replay instances to be compared against.
            Integer threshold: If a comparison scores below this value, the result is printed.
        """
```

Classes and methods may reference another class or method that is highly relevant to them. This should be used sparingly, when knowing of both in the context of each other gives greater understanding to the program. This extra section is placed below all others, and is the only section without a period at the end of each sentence.

```python
class ClassA:
    """
    Does something.

    See Also:
        ClassB
    """
```


### Actual Code

Where possible, list comprehensions are generally prefered over lambdas.

```python
my_list = [x for x in my_list if x.attribute == value] # PREFERRED
my_list = filter(lambda x: x.attribute == value, my_list) # NOT PREFERRED
```

However, note that there are multiple places a lambda is more reabable, such as sorting an array:
```python
stats.sort(key=lambda stat: stat[0])
```

## Github

Follow general git conventions when committing:

* Do not exceed 72 characters in the commit summary
* Start the description with a verb in the imeprative mood (`fix` (good) vs `fixes` (bad))
* Start descriptions with a lowercase letter
* If the commit addresses a specific issue, reference that issue at the end of the commit summary (`use different graphical backend (closes #6)`)

Pull Requests with messy history may be converted to a squash merge at a mantainer's discretion.

Finally, thou shalt not commit directly to master.
