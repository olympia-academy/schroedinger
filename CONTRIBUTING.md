# Contributing

Install the editable package and tests with `python -m pip install -e ".[test]"`.
Run `python -m pytest -q` before proposing changes.

Use a branch for each coherent change and a pull request for review. Describe
the physical problem, what behavior changes, and the numerical evidence.
Both collaborators should review solver or boundary-condition changes before
merging. The default branch should require passing tests and one review.

For numerical work:
- Specify hbar, mass, initial state, grid, boundary conditions and physical final time.
- Check norm without an absorber; with an absorber, check norm plus measured loss.
- Refine dt and spatial resolution separately, keeping physical time and geometry comparable.
- Use analytic solutions or an independent reference wherever available.
- Report effective rasterized wall/slit widths when comparing grids.
- Preserve author attribution and the original project's references.

Treat demo defaults as qualitative settings. A prettier animation is not
evidence of improved accuracy. Keep generated plots, local environments,
caches and result files out of commits.
