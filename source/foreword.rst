Foreword
========

The following pages serve as an introduction to circlecore. Although they
would ideally be exhaustive, they are likely not. Refer to the source
documentation where this introduction fails you. You are also welcome to ask
questions on our `discord Discord_`_

To aid in readability, ``import`` statements have been ommitted from code
blocks. Please supply your own.

Because the `osu api`_ places rather heavy ratelimits (10 per minute) on
loading replays, a low quantity of replays has been used where appropriate
in the examples, to reduce frustration should you choose to try the provided
code. Know that the api (and subsequently circlecore) supports loading
up to 100 top scores from a map or user.

osu! stores the top 1000 scores of a map, but only provides the first 100 as
automatically discoverable through the api. Should you know about a specific
score outside of the top 1000 on a map, you can still load and investigate it
through circlecore.
