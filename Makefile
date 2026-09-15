.PHONY: help validate bootstrap-ubuntu22 build-ueransim assurance-test preflight render-ueransim render-asterisk provision-seven host-evidence generate-identities generate-esim

help:
	@echo "MINI-MOBILE-7 commands:"
	@echo "  make validate          - validate the Linux host prerequisites"
	@echo "  make bootstrap-ubuntu22 - install pinned lab host prerequisites"
	@echo "  make build-ueransim   - build pinned UERANSIM"
	@echo "  make assurance-test   - run Project-72 assurance, adapter, lifecycle, idempotency, concurrency, renderer, identity/eSIM and runtime-wiring tests"
	@echo "  make preflight        - run the Project-72 runtime safety gate"
	@echo "  make render-ueransim  - render deployment-local UE configs from external secrets"
	@echo "  make render-asterisk  - render deployment-local seven-subscriber PJSIP endpoints from external secrets"
	@echo "  make provision-seven   - dry-run seven-subscriber runtime provisioning"
	@echo "  make host-evidence    - collect read-only host acceptance evidence"
	@echo "  make generate-identities - print deterministic private identities 7001-7007"
	@echo "  make generate-esim    - run eSIM artifact unit tests without contacting an SM-DP+"

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
		project_72.assurance_core.test_idempotency_concurrency \
		project_72.assurance_core.test_concurrency \
		project_72.assurance_core.test_runtime_wiring \
		project_72.assurance_core.test_ueransim_renderer \
		project_72.assurance_core.test_asterisk_renderer \
		project_72.assurance_core.test_identity_esim \
		project_72.assurance_core.test_esim_assurance \
		adapters.open5gs.test_adapter \
		adapters.open5gs.test_assurance_integration -v

preflight:
	bash scripts/project-72-preflight.sh

render-ueransim:
	bash scripts/project-72-render-ueransim.sh

render-asterisk:
	bash scripts/project-72-render-asterisk-pjsip.sh

provision-seven:
	PYTHONPATH=. python3 scripts/project-72-provision-seven.py

host-evidence:
	bash scripts/project-72-host-evidence.sh

generate-identities:
	PYTHONPATH=. python3 -c 'from project_72.assurance_core.identity import IdentityGenerator; [print(f"{x.subscriber_id} {x.extension} {x.sip_uri} {x.tel_uri}") for x in IdentityGenerator().generate_all()]'

generate-esim:
	PYTHONPATH=. python3 -m unittest project_72.assurance_core.test_identity_esim project_72.assurance_core.test_esim_assurance -v
