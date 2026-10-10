# McNemar tests: ReAct vs no-ReAct

Rule: a task counts as correct in a condition if >= 50% of its reps were correct. Exact (two-sided) McNemar; `p_mid` = mid-p variant; `p_holm` = Holm over the 7 categories (ALL excluded, its `sig` uses the raw p). `odds_ratio` = (react_only+.5)/(no_react_only+.5). sig: * p<0.05, ** p<.01, *** p<.001 (adjusted), ns = not significant.

| group | n_tasks | acc_react | acc_no_react | diff | react_only | no_react_only | odds_ratio | p_exact | p_mid | p_holm | direction | sig |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL | 180 | 0.9111 | 0.4889 | 0.4222 | 80 | 4 | 17.8889 | 0.0000 | 0.0000 |  | ReAct better | *** |
| calculator | 30 | 0.9667 | 0.7333 | 0.2333 | 8 | 1 | 5.6667 | 0.0391 | 0.0215 | 0.1562 | ReAct better | ns |
| datetime | 30 | 0.8667 | 0.0333 | 0.8333 | 25 | 0 | 51.0000 | 0.0000 | 0.0000 | 0.0000 | ReAct better | *** |
| multi_tool | 20 | 0.9000 | 0.2000 | 0.7000 | 15 | 1 | 10.3333 | 0.0005 | 0.0003 | 0.0026 | ReAct better | ** |
| no_tool | 30 | 1.0000 | 0.9000 | 0.1000 | 3 | 0 | 7.0000 | 0.2500 | 0.1250 | 0.6562 | ReAct better | ns |
| weather | 20 | 1.0000 | 0.0000 | 1.0000 | 20 | 0 | 41.0000 | 0.0000 | 0.0000 | 0.0000 | ReAct better | *** |
| web_search | 20 | 0.6000 | 0.4000 | 0.2000 | 5 | 1 | 3.6667 | 0.2188 | 0.1250 | 0.6562 | ReAct better | ns |
| wikipedia | 30 | 0.9667 | 0.8667 | 0.1000 | 4 | 1 | 3.0000 | 0.3750 | 0.2188 | 0.6562 | ReAct better | ns |

## Contingency tables

**ALL** (n=180)

|  | no-ReAct correct | no-ReAct wrong |
|---|---|---|
| **ReAct correct** | 84 | 80 |
| **ReAct wrong** | 4 | 12 |

**calculator** (n=30)

|  | no-ReAct correct | no-ReAct wrong |
|---|---|---|
| **ReAct correct** | 21 | 8 |
| **ReAct wrong** | 1 | 0 |

**datetime** (n=30)

|  | no-ReAct correct | no-ReAct wrong |
|---|---|---|
| **ReAct correct** | 1 | 25 |
| **ReAct wrong** | 0 | 4 |

**multi_tool** (n=20)

|  | no-ReAct correct | no-ReAct wrong |
|---|---|---|
| **ReAct correct** | 3 | 15 |
| **ReAct wrong** | 1 | 1 |

**no_tool** (n=30)

|  | no-ReAct correct | no-ReAct wrong |
|---|---|---|
| **ReAct correct** | 27 | 3 |
| **ReAct wrong** | 0 | 0 |

**weather** (n=20)

|  | no-ReAct correct | no-ReAct wrong |
|---|---|---|
| **ReAct correct** | 0 | 20 |
| **ReAct wrong** | 0 | 0 |

**web_search** (n=20)

|  | no-ReAct correct | no-ReAct wrong |
|---|---|---|
| **ReAct correct** | 7 | 5 |
| **ReAct wrong** | 1 | 7 |

**wikipedia** (n=30)

|  | no-ReAct correct | no-ReAct wrong |
|---|---|---|
| **ReAct correct** | 25 | 4 |
| **ReAct wrong** | 1 | 0 |
