# Style

This document lays out the agreed upon style for code and commits to this repository.

## Code

### Docstrings

For docstrings, follow [google's style](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings), with the following differences:

* Unless the docstring is only one line, docstrings should begin with a newline  (documentation should not go on the same line as the triple quotes)


### General

Where possible, list comprehension is prefered over lambdas.

```python
my_list = [x for x in my_list if x.attribute == value] # PREFERRED
my_list = filter(lambda x: x.attribute == value, my_list) # NOT PREFERRED
```

However, note that there are multiple places a lambda is more reabable, such as sorting an array:
```python
stats.sort(key=lambda stat: stat[0])
```

## Github

### Committing 

Follow general git conventions when committing:

* Do not exceed 80 characters in the commit summary
* Start the description with a verb in the imeprative mood (`fix` (good) vs `fixes` (bad))
* Start descriptions with a lowercase letter
* If the commit addresses a specific issue, reference that issue in the commit summary (`closes #6`)

Pull Requests with messy history may be converted to a squash merge at the mantainer's disgression.

Finally, thou shalt not commit directly to master.