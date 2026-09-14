.PHONY: help validate bootstrap-ubuntu22 build-ueransim assurance-test preflight provision-seven

help:
	@echo "MINI-MOBILE-7 commands:"
	@echo "  make validate          - validate the Linux host prerequisites"
	@echo "  make bootstrap-ubuntu22 - install pinned lab host prerequisites"
	@echo "  make build-ueransim   - build pinned UERANSIM"
	@echo "  make assurance-test   - run Project-72 assurance, adapter and lifecycle tests"
	@echo "  make preflight        - run the Project-72 runtime safety gate"
	@echo "  make provision-seven  - dry-run seven-subscriber runtime provisioning"

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
		adapters.open5gs.test_adapter \
		adapters.open5gs.test_assurance_integration -v

preflight:
	bash scripts/project-72-preflight.sh

provision-seven:
	PYTHONPATH=. python3 scripts/project-72-provision-seven.py
