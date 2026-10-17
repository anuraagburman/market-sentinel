# Synthetic provider wire payloads

Every value and identity here is invented. `.payload` files contain JSON in the vendor's wire
shape, not canonical Market Sentinel entities. They deliberately use a different suffix because
the eval fixture gate treats every `.json` file as a canonical entity. `test_providers.py` reads
these wire payloads and validates the resulting Observation/Evidence with format checking enabled.

Calendar: regular sessions across US DST and an early close. Bars: a synthetic 2:1 split,
precision beyond binary float, and zero volume. Submissions/history: distinct filing and acceptance
clocks, recent metadata, and a historical page. Failure variants are constructed in deterministic
tests from these synthetic seeds; no tests access the network.
