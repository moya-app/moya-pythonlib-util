# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/moya-app/moya-pythonlib-util/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                 |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------- | -------: | -------: | ------: | --------: |
| moya/\_\_init\_\_.py                 |        0 |        0 |    100% |           |
| moya/middleware/\_\_init\_\_.py      |        0 |        0 |    100% |           |
| moya/middleware/connection\_stats.py |       54 |        3 |     94% | 35, 46-47 |
| moya/middleware/gzip\_route.py       |       25 |        0 |    100% |           |
| moya/middleware/http\_cache.py       |       47 |        2 |     96% |    33, 87 |
| moya/middleware/multipleslashes.py   |       15 |        0 |    100% |           |
| moya/service/\_\_init\_\_.py         |        0 |        0 |    100% |           |
| moya/service/id.py                   |       30 |        1 |     97% |        43 |
| moya/service/kafka.py                |       55 |        0 |    100% |           |
| moya/service/kafka\_consumer.py      |       35 |       13 |     63% |62-68, 71-72, 75-76, 79, 82 |
| moya/service/kafka\_producer.py      |       29 |        5 |     83% | 63-66, 92 |
| moya/service/kafka\_runner.py        |       64 |       64 |      0% |     1-158 |
| moya/service/redis.py                |      152 |       18 |     88% |45-48, 176, 214, 246-247, 283, 327-339 |
| moya/service/url\_checker.py         |       27 |        0 |    100% |           |
| moya/util/\_\_init\_\_.py            |        0 |        0 |    100% |           |
| moya/util/argparse.py                |       26 |        0 |    100% |           |
| moya/util/asyncpool.py               |       29 |        0 |    100% |           |
| moya/util/autoenum.py                |        6 |        0 |    100% |           |
| moya/util/background.py              |       38 |        5 |     87% |31-32, 94-95, 100 |
| moya/util/background\_tasks.py       |       36 |        0 |    100% |           |
| moya/util/beartype.py                |        8 |        0 |    100% |           |
| moya/util/cmd.py                     |       13 |        0 |    100% |           |
| moya/util/config.py                  |        4 |        0 |    100% |           |
| moya/util/enum.py                    |       14 |        1 |     93% |        23 |
| moya/util/fastapi.py                 |       52 |        9 |     83% |     40-56 |
| moya/util/fastapi\_ratelimit.py      |       51 |        0 |    100% |           |
| moya/util/logging.py                 |       11 |        0 |    100% |           |
| moya/util/ratelimit.py               |       92 |        4 |     96% |62, 75, 82, 89 |
| moya/util/sentry.py                  |       18 |        0 |    100% |           |
| moya/util/test/\_\_init\_\_.py       |        0 |        0 |    100% |           |
| moya/util/test/expected.py           |       22 |        0 |    100% |           |
|                            **TOTAL** |  **953** |  **125** | **87%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/moya-app/moya-pythonlib-util/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/moya-app/moya-pythonlib-util/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/moya-app/moya-pythonlib-util/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/moya-app/moya-pythonlib-util/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fmoya-app%2Fmoya-pythonlib-util%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/moya-app/moya-pythonlib-util/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.