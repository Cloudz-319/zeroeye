.PHONY: install-hooks uninstall-hooks help

HOOK_SRC := tools/pre-commit
HOOK_DST := .git/hooks/pre-commit

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-hooks: ## Install the pre-commit hook into .git/hooks/
	@echo "Installing pre-commit hook..."
	@mkdir -p .git/hooks
	@cp $(HOOK_SRC) $(HOOK_DST)
	@chmod +x $(HOOK_DST)
	@echo "Done. Pre-commit hook installed at $(HOOK_DST)"
	@echo "The hook will run build.py and stage diagnostic artifacts before each commit."

uninstall-hooks: ## Remove the pre-commit hook from .git/hooks/
	@echo "Removing pre-commit hook..."
	@rm -f $(HOOK_DST)
	@echo "Done. Pre-commit hook removed."

clean-diagnostics: ## Remove cached diagnostic hash files
	@rm -f .git/.diagnostic-hashes
	@echo "Diagnostic hash cache cleared."
