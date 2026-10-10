# Results

ReAct clearly outperforms the plain model overall. Across all 180 tasks it reached about 0.91 accuracy against 0.49 without it. The two conditions disagreed on 84 tasks and ReAct won 80 of them (McNemar, p < 0.001).

## Where the gain comes from

The gain is concentrated in categories that need live or computed information. Weather (1.00 vs 0.00), datetime (0.87 vs 0.03) and multi_tool (0.90 vs 0.20) are all significant after Holm correction. In weather and datetime the plain model cannot know the current conditions or date, and its baseline prompt tells it to say so, so these gaps measure access to tools rather than reasoning ability.

The remaining categories show smaller gaps that are not significant: calculator (0.97 vs 0.73), wikipedia (0.97 vs 0.87), no_tool (1.00 vs 0.90) and web_search (0.60 vs 0.40). With only 20 to 30 tasks per category the test has little power, so "not significant" does not mean "no difference". Calculator is the clearest case, with 8 ReAct-only wins against 1 for the plain model, which did not survive the correction across seven categories.

## Points worth noting

On no_tool tasks ReAct did not lose accuracy (it won 3 tasks and lost none), so there is no sign of a penalty when tools are unnecessary. The charts do not show whether it called tools needlessly, which is reported separately in report.md. Web search is ReAct's weakest category at 0.60, and the discordant and failed rows should be read to see whether the cause is retrieval, outdated expected answers or step limits.

## Caveats

The ALL bar pools tasks by count, and 150 of the 180 tasks are tool-oriented, so it overstates the typical gain. The comparison is the full agent against the bare model, so the improvement bundles tool access, the ReAct format and the long system prompt, and cannot be credited to the ReAct format alone. These charts show accuracy only, so confidence intervals, latency and failure types need to come from report.md before drawing final conclusions.