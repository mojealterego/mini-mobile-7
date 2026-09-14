.PHONY: help validate bootstrap-ubuntu22 build-ueransim assurance-test preflight render-ueransim provision-seven

help:
	@echo "MINI-MOBILE-7 commands:"
	@echo "  make validate          - validate the Linux host prerequisites"
	@echo "  make bootstrap-ubuntu22 - install pinned lab host prerequisites"
	@echo "  make build-ueransim   - build pinned UERANSIM"
	@echo "  make assurance-test   - run Project-72 assurance, adapter, lifecycle, idempotency, concurrency and runtime-wiring tests"
	@echo "  make preflight        - run the Project-72 runtime safety gate"
	@echo "  make render-ueransim  - render deployment-local UE configs from external secrets"
	@echo "  make provision-seven   - dry-run seven-subscriber runtime provisioning"

validate:
	bash scripts/validate-host.sh

bootstrap-ubuntu22:
	bash scripts/bootstrap-ubuntu22.sh

build-ueransim:
	bash scripts/build-ueransim.sh

assurance-test:
	PYTHONPATH=. python3 -m unittest \
		project_72.assurance_core.test_golden_path \
		project_72.assurance_core.test_drift \
		project_72.assurance_core.test_lifecycle \
		project_72.assurance_core.test_idempotency \
		project_72.assurance_core.test_concurrency \
		project_72.assurance_core.test_runtime_wiring \
		adapters.open5gs.test_adapter \
		adapters.open5gs.test_assurance_integration -v

preflight:
	bash scripts/project-72-preflight.sh

render-ueransim:
	bash scripts/project-72-render-ueransim.sh

provision-seven:
	PYTHONPATH=. python3 scripts/project-72-provision-seven.py
